# Kubernetes高可用集群

> Kubernetes是容器集群管理系统，是一个开源的平台，可以实现容器集群的自动化部署、自动扩缩容、维护等功能。
>
> 通过Kubernetes你可以：
>
> - 快速部署应用
> - 快速扩展应用
> - 无缝对接新的应用功能
> - 节省资源，优化硬件资源的使用
>
> Kubernetes特点：
>
> - **可移植**：支持公有云、私有云、混合云、多重云
> - **可扩展**：模块化、插件化、可挂载、可组合
> - **自动化**：自动部署、自动重启、自动复制、自动伸缩/扩展
>



> etcd是 CoreOS 团队发起的开源项目，基于 Go 语言实现，做为一个分布式键值对存储，通过分布式锁，leader选举和写屏障(write barriers)来实现可靠的分布式协作。主要用于分享配置和服务发现。
>
> - 简单：支持 curl 方式的用户 API (HTTP+JSON) 
> - 安全：可选 SSL 客户端证书认证 
> - 快速：单实例可达每秒1000次写操作 
> - 可靠：使用 Raft 实现分布式



## 节点构造如下 :

| 节点ip        | 节点角色 | hostname |
| ------------- | -------- | -------- |
| 172.16.71.8   | etcd     | etcd01   |
| 172.16.71.9   | etcd     | etcd02   |
| 172.16.71.10  | etcd     | etcd03   |
| 172.16.70.65  | master   | master01 |
| 172.16.70.66  | master   | master02 |
| 172.16.70.67  | master   | master03 |
| 172.16.70.68  | node     | node01   |
| 172.16.70.161 | node     | node02   |
| 172.16.70.162 | node     | node03   |

## 集群网络结构：

| 网络名称         | 网络范围      |
| ---------------- | ------------- |
| Physical Network | 172.16.0.0/12 |
| Service Network  | 10.64.0.0/12  |
| Pod Network      | 10.80.0.0/12  |

### 组件配置：

| 系统               | 参数               |
| ------------------ | ------------------ |
| 系统               | CentOS 7.6  x86_64 |
| 内核版本           | 3.10               |
| docker-data数据盘  | xfs                |
| docker-ce          | 18.06.1            |
| kubernetes         | 1.13.2             |
| Storage Driver     | overlay2           |
| Backing Filesystem | extfs              |
| Logging Driver     | json-file          |
| Cgroup Driver      | systemd            |



## 一、安装前准备

###1、安装Docker和kubernets

####1.2、所有节点安装Docker, 修改文件系统为ovelay2驱动

```
#安装docker
yum -y install yum-utils device-mapper-persistent-data lvm2
yum-config-manager --add-repo http://mirrors.aliyun.com/docker-ce/linux/centos/docker-ce.repo
yum makecache fast
yum -y install docker-ce


#设置文件系统为ovelay2驱动
cat /etc/docker/daemon.json
{
 "registry-mirrors": ["https://registry.docker-cn.com"],
 "exec-opts": ["native.cgroupdriver=systemd"],
 "storage-driver": "overlay2",
 "storage-opts":["overlay2.override_kernel_check=true"],
 "log-driver": "json-file",
 "log-opts": {
     "max-size": "100m",
     "max-file": "10"
 },
 "oom-score-adjust": -1000,
 "graph": "/data/data/docker"
}

systemctl daemon-reload && systemctl start docker
```

#### 1.3、配置安装kubernetes

```
#master节点
wget http://dl.anymb.com/k8s/1.13.2/kube-apiserver -P /usr/bin/
wget http://dl.anymb.com/k8s/1.13.2/kube-controller-manager -P /usr/bin/
wget http://dl.anymb.com/k8s/1.13.2/kube-scheduler -P /usr/bin/
wget http://dl.anymb.com/k8s/1.13.2/kube-aggregator -P /usr/bin/
#管理集群使用
wget http://dl.anymb.com/k8s/1.13.2/kubectl -P /usr/bin/
chmod +x /usr/bin/kube*
#node节点
wget http://dl.anymb.com/k8s/1.13.2/kubelet -P /usr/bin/
wget http://dl.anymb.com/k8s/1.13.2/kube-proxy -P /usr/bin/
chmod +x /usr/bin/kube*

#创建k8s运行用户
groupadd -g 200 kube
useradd -g kube kube -u 200 -d / -s /sbin/nologin -M

yum install -y libnetfilter_conntrack-devel libnetfilter_conntrack conntrack-tools

#此操作为解决问题: Failed to delete stale service IP 10.0.0.10 connections, error: error deleting connection tracking state for UDP service IP: 10.0.0.10, error: error looking for path of conntrack: exec: "conntrack": executable file not found in $PATH
```



###2、配置集群证书

####2.1、签发证书

##### 2.1.1、签发CA证书

a)、准备ca配置文件ca.cnf

```
[ req ]
req_extensions = v3_req
distinguished_name = req_distinguished_name
[req_distinguished_name]

[ v3_req ]
keyUsage = critical, cRLSign, keyCertSign, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth, clientAuth
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid:always,issuer
basicConstraints = critical, CA:true, pathlen:2
```

b)、创建ca key

```
openssl genrsa -out ca.key 3072
```

c)、签发ca

```
openssl req -x509 -new -nodes -key ca.key -days 1825 -out ca.pem -subj "/CN=kubernetes/OU=System/C=CN/ST=Shanghai/L=Shanghai/O=k8s" -config ca.cnf -extensions v3_req
```

  - 有效期1825(d)=5years

  - 注意 -subj 参数中仅 'C=CN' 与 'Shanghai' 可以修改，**其它保持原样**，否则集群会遇到权限异常问题


##### 2.1.2、签发API Server证书

a)、准备apiserver.cnf配置文件

```
[ req ]
req_extensions = v3_req
distinguished_name = req_distinguished_name
[req_distinguished_name]
[ v3_req ]
basicConstraints = critical, CA:FALSE
keyUsage = critical, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth, clientAuth
#subjectKeyIdentifier = hash
#authorityKeyIdentifier = keyid:always,issuer
subjectAltName = @alt_names
[alt_names]
DNS.1 = kubernetes
DNS.2 = kubernetes.default
DNS.3 = kubernetes.default.svc
DNS.4 = kubernetes.default.svc.cluster
DNS.5 = kubernetes.default.svc.cluster.local
DNS.6 = apiserver.msfar.cn
IP.1 = 172.16.70.65
IP.2 = 172.16.70.66
IP.3 = 172.16.70.67
IP.4 = 10.64.0.1
IP.5 = 172.16.70.163
```

- IP.4 是service 第一个IP
- IP.5 是HA VIP，方便API Server后期高可用。IP.1-IP.3是API Server IP

b)、生成key

```
openssl genrsa -out apiserver.key 3072
```

c)、生成证书请求

```
openssl req -new -key apiserver.key -out apiserver.csr -subj "/CN=kubernetes/OU=System/C=CN/ST=Shanghai/L=Shanghai/O=k8s" -config apiserver.cnf
```

- CN、OU、O 字段为认证时使用, 请勿修改
- 注意 -subj 参数中仅 'C'、'ST' 与 'L' 可以修改，**其它保持原样**，否则集群会遇到权限异常问题

d)、签发证书

```
openssl x509 -req -in apiserver.csr -CA ca.pem -CAkey ca.key -CAcreateserial -out apiserver.pem -days 1825 -extfile apiserver.cnf -extensions v3_req
```

- 注意: 需要先去掉 apiserver.cnf 注释掉的两行


##### 2.1.3、签发etcd证书

a)、准备etcd.cnf配置文件

```
[ req ]
req_extensions = v3_req
distinguished_name = req_distinguished_name
[req_distinguished_name]
[ v3_req ]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
subjectAltName = @alt_names
[alt_names]
IP.1 = ${IP_ADDR}
```

- etcd集群用证书。IP.1 是对应节点IP

b)、生成key

```
openssl genrsa -out etcd_${IP_ADDR}.key 3072
```

c)、生成证书请求

```
openssl req -new -key etcd_${IP_ADDR}.key -out etcd_${IP_ADDR}.csr -subj "/CN=etcd/OU=System/C=CN/ST=Shanghai/L=Shanghai/O=k8s" -config etcd_${IP_ADDR}.cnf
```

- CN=etcd

d)、签发证书

```
openssl x509 -req -in etcd_${IP_ADDR}.csr -CA ca.pem -CAkey ca.key -CAcreateserial -out etcd_${IP_ADDR}.pem -days 1825 -extfile etcd_${IP_ADDR}.cnf -extensions v3_req
```



#####2.1.4、签发kubelet证书

a)、准备kubelet.cnf配置文件

```
[ req ]
req_extensions = v3_req
distinguished_name = req_distinguished_name
[req_distinguished_name]
[ v3_req ]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
subjectAltName = @alt_names
[alt_names]
IP.1 = ${IP_ADDR}
```

- 为master和node节点签发kubelet证书
- IP.1 是对应节点IP

b)、生成key

```
openssl genrsa -out kubelet_${IP_ADDR}.key 3072
```

c)、生成证书请求

```
openssl req -new -key kubelet_${IP_ADDR}.key -out kubelet_${IP_ADDR}.csr -subj "/CN=admin/OU=System/C=CN/ST=Shanghai/L=Shanghai/O=system:masters" -config kubelet_${IP_ADDR}.cnf
```

- CN=admin,O=system:masters

d)、签发证书

```
openssl x509 -req -in kubelet_${IP_ADDR}.csr -CA ca.pem -CAkey ca.key -CAcreateserial -out kubelet_${IP_ADDR}.pem -days 1825 -extfile kubelet_${IP_ADDR}.cnf -extensions v3_req
```



##### 2.1.5、签发kube-proxy证书

a)、准备kube-proxy.cnf配置文件

```
[ req ]
req_extensions = v3_req
distinguished_name = req_distinguished_name
[req_distinguished_name]
[ v3_req ]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
subjectAltName = @alt_names
[alt_names]
IP.1 = ${IP_ADDR}
```

- node节点签发证书，IP.1 是对应节点IP

b)、生成key

```
openssl genrsa -out kube-proxy_${IP_ADDR}.key 3072
```

c)、生成证书请求

```
openssl req -new -key kube-proxy_${IP_ADDR}.key -out kube-proxy_${IP_ADDR}.csr -subj "/CN=system:kube-proxy/OU=System/C=CN/ST=Shanghai/L=Shanghai/O=k8s" -config kube-proxy_${IP_ADDR}.cnf
```

- CN=system,O=k8s

d)、签发证书

```
openssl x509 -req -in kube-proxy_${IP_ADDR}.csr -CA ca.pem -CAkey ca.key -CAcreateserial -out kube-proxy_${IP_ADDR}.pem -days 1825 -extfile kube-proxy_${IP_ADDR}.cnf -extensions v3_req
```



##### 2.1.6、签发flannel证书

a)、准备flannel.cnf配置文件

```
[ req ]
req_extensions = v3_req
distinguished_name = req_distinguished_name
[req_distinguished_name]
[ v3_req ]
basicConstraints = critical, CA:FALSE
keyUsage = critical, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth, clientAuth
subjectAltName = @alt_names
[ alt_names ]
IP.1 = ${IP_ADDR}
```

- 为master和node节点签发证书，可通过本证书连接etcd
- IP.1为各节点IP

b)、生成key

```
openssl genrsa -out flannel_${IP_ADDR}.key 3072
```

c)、生成证书请求

```
openssl req -new -key flannel_${IP_ADDR}.key -out flannel_${IP_ADDR}.csr -subj "/CN=flannel/OU=System/C=CN/ST=Shanghai/L=Shanghai/O=k8s" -config flannel_${IP_ADDR}.cnf
```

- CN=flannel,O=k8s

d)、签发证书

```
openssl x509 -req -in flannel_${IP_ADDR}.csr -CA ca.pem -CAkey ca.key -CAcreateserial -out flannel_${IP_ADDR}.pem -days 1825 -extfile flannel_${IP_ADDR}.cnf -extensions v3_req
```

#### 2.2、验证证书是否正常

```
openssl x509  -noout -text -in apiserver.pem
```



### 3、配置etcd集群

#### 3.1、拷贝证书

```
scp ca.pem ${IP_ADDR}:/etc/etcd/ssl
scp etcd_${IP_ADDR}.key ${IP_ADDR}:/etc/etcd/ssl
scp etcd_${IP_ADDR}.pem ${IP_ADDR}:/etc/etcd/ssl
```



#### 3.2、配置etcd

安装etcd

```
yum -y install etcd
```

##### 3.2.1、etcd主配置文件

```
[member]
ETCD_NAME=etcd03
ETCD_DATA_DIR="/data/data/etcd"
ETCD_LISTEN_PEER_URLS="https://172.16.71.10:2380"
ETCD_LISTEN_CLIENT_URLS="https://172.16.71.10:2379"
[cluster]
ETCD_INITIAL_ADVERTISE_PEER_URLS="https://172.16.71.10:2380"
ETCD_INITIAL_CLUSTER="etcd01=https://172.16.71.8:2380,etcd02=https://172.16.71.9:2380,etcd03=https://172.16.71.10:2380"
ETCD_INITIAL_CLUSTER_STATE="new"
ETCD_ADVERTISE_CLIENT_URLS="https://172.16.71.10:2379"
[security]
ETCD_CERT_FILE="/etc/etcd/ssl/etcd_172.16.71.10.pem"
ETCD_KEY_FILE="/etc/etcd/ssl/etcd_172.16.71.10.key"
ETCD_CLIENT_CERT_AUTH="true"
ETCD_TRUSTED_CA_FILE="/etc/kubernetes/ssl/ca.pem"
ETCD_AUTO_TLS="true"
ETCD_PEER_CERT_FILE="/etc/etcd/ssl/etcd_172.16.71.10.pem"
ETCD_PEER_KEY_FILE="/etc/etcd/ssl/etcd_172.16.71.10.key"
ETCD_PEER_CLIENT_CERT_AUTH="true"
ETCD_PEER_TRUSTED_CA_FILE="/etc/kubernetes/ssl/ca.pem"
ETCD_PEER_AUTO_TLS="true"
```

- 对应ip、名称请修改为对应节点ip、名称

#####3.2.2、etcd主配置文件

```
[Unit]
Description=Etcd Server
After=network.target
After=network-online.target
Wants=network-online.target

[Service]
Type=notify
WorkingDirectory=/data/data/etcd/
EnvironmentFile=-/etc/etcd/etcd.conf
User=etcd

ExecStart=/bin/bash -c "GOMAXPROCS=$(nproc) /usr/bin/etcd \
    --name=\"${ETCD_NAME}\" \
    --cert-file=\"${ETCD_CERT_FILE}\" \
    --key-file=\"${ETCD_KEY_FILE}\" \
    --peer-cert-file=\"${ETCD_PEER_CERT_FILE}\" \
    --peer-key-file=\"${ETCD_PEER_KEY_FILE}\" \
    --trusted-ca-file=\"${ETCD_TRUSTED_CA_FILE}\" \
    --peer-trusted-ca-file=\"${ETCD_PEER_TRUSTED_CA_FILE}\" \
    --initial-advertise-peer-urls=\"${ETCD_INITIAL_ADVERTISE_PEER_URLS}\" \
    --listen-peer-urls=\"${ETCD_LISTEN_PEER_URLS}\" \
    --listen-client-urls=\"${ETCD_LISTEN_CLIENT_URLS}\" \
    --advertise-client-urls=\"${ETCD_ADVERTISE_CLIENT_URLS}\" \
    --initial-cluster-token=\"${ETCD_INITIAL_CLUSTER_TOKEN}\" \
    --initial-cluster=\"${ETCD_INITIAL_CLUSTER}\" \
    --initial-cluster-state=\"${ETCD_INITIAL_CLUSTER_STATE}\" \
    --data-dir=\"${ETCD_DATA_DIR}\""

Restart=on-failure
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

##### 3.2.3、创建etcd数据目录

```
mkdir /data/data/etcd
chown -R etcd. /data/data/etcd
```

##### 3.2.4、启动集群,并验证

```
#启动etcd集群
for node in {etcd01,etcd02,etcd03};do
    ssh ${node} "systemctl daemon-reload && systemctl start etcd && systemctl enable etcd"
done
```

```
etcdctl --endpoints=https://172.16.70.9:2379 \
                        --ca-file=/etc/kubernetes/ssl/ca.pem \
                        --cert-file=/etc/etcd/ssl/etcd_172.16.70.9.pem \
                        --key-file=/etc/etcd/ssl/etcd_172.16.70.9.key \
                        member list
```

```
#将节点加入集群
etcdctl --endpoints=https://172.16.70.9:2379 \
                        --ca-file=/etc/kubernetes/ssl/ca.pem \
                        --cert-file=/etc/etcd/ssl/etcd_172.16.70.9.pem \
                        --key-file=/etc/etcd/ssl/etcd_172.16.70.9.key \
                        member add etcd04 https://172.16.70.11:2380
                        
#以下配置项修改为existing
ETCD_INITIAL_CLUSTER_STATE="existing"
```

#### 3.3、为flannel增加网络配置

##### 3.3.1、创建目录

```
etcdctl --endpoints=https://172.16.70.9:2379 \
                        --ca-file=/etc/kubernetes/ssl/ca.pem \
                        --cert-file=/etc/etcd/ssl/etcd_172.16.70.9.pem \
                        --key-file=/etc/etcd/ssl/etcd_172.16.70.9.key \
                        mkdir /k8s/network
```

##### 3.3.2、设置网络

```
etcdctl --endpoints=https://172.16.70.9:2379 \
                        --ca-file=/etc/kubernetes/ssl/ca.pem \
                        --cert-file=/etc/etcd/ssl/etcd_172.16.70.9.pem \
                        --key-file=/etc/etcd/ssl/etcd_172.16.70.9.key \
                        set /k8s/network/config '{"Network": "10.80.0.0/12","Backend": {"Type": "vxlan"}}'
```

##### 2.3.3、查看已分配网络

```
etcdctl --endpoints=https://172.16.70.9:2379 \
                        --ca-file=/etc/kubernetes/ssl/ca.pem \
                        --cert-file=/etc/etcd/ssl/etcd_172.16.70.9.pem \
                        --key-file=/etc/etcd/ssl/etcd_172.16.70.9.key \
                        get /k8s/network/config
```



### 4、配置flannel

#### 4.1、拷贝证书

```
scp flannel_${IP_ADDR}.key ${IP_ADDR}:/etc/kubernetes/ssl/
scp flannel_${IP_ADDR}.pem ${IP_ADDR}:/etc/kubernetes/ssl/
scp ca.pem ${IP_ADDR}:/etc/kubernetes/ssl/
```

#### 4.2、为master和node节点安装flannel

```
wget https://github.com/coreos/flannel/releases/download/v0.10.0/flannel-v0.10.0-linux-amd64.tar.gz
tar zxvf flannel-v0.10.0-linux-amd64.tar.gz
mkdir /usr/libexec/flannel
mv flanneld /usr/bin/
mv mk-docker-opts.sh /usr/libexec/flannel/
```

vim /usr/bin/flanneld-start

```
#!/bin/sh

exec /usr/bin/flanneld \
    -etcd-endpoints=${FLANNEL_ETCD_ENDPOINTS:-${FLANNEL_ETCD}} \
    -etcd-prefix=${FLANNEL_ETCD_PREFIX:-${FLANNEL_ETCD_KEY}} \
    "$@"
```

```
chmod 755 /usr/bin/flanneld /usr/libexec/flannel/mk-docker-opts.sh /usr/bin/flanneld-start
```

#### 4.3、配置flannel

vim /etc/kubernetes/flanneld

```
# Flanneld configuration options
# etcd url location.  Point this to the server where etcd runs
FLANNEL_ETCD_ENDPOINTS="https://172.16.71.8:2379,https://172.16.71.9:2379,https://172.16.71.10:2379"

# etcd config key.  This is the configuration key that flannel queries
# For address range assignment
FLANNEL_ETCD_PREFIX="/k8s/network"

# Any additional options that you want to pass
FLANNEL_OPTIONS="-etcd-cafile=/etc/kubernetes/ssl/ca.pem -etcd-certfile=/etc/kubernetes/ssl/flannel_172.16.70.65.pem -etcd-keyfile=/etc/kubernetes/ssl/flannel_172.16.70.65.key"
```

- 请将示例中ip修改为对应节点IP

vim /usr/lib/systemd/system/flanneld.service

```
[Unit]
Description=Flanneld overlay address etcd agent
After=network.target
After=network-online.target
Wants=network-online.target
After=etcd.service
Before=docker.service

[Service]
Type=notify
EnvironmentFile=/etc/kubernetes/flanneld
EnvironmentFile=-/etc/sysconfig/docker-network
ExecStart=/usr/bin/flanneld-start $FLANNEL_OPTIONS
ExecStartPost=/usr/libexec/flannel/mk-docker-opts.sh -k DOCKER_NETWORK_OPTIONS -d /run/flannel/docker
Restart=on-failure

[Install]
WantedBy=multi-user.target
WantedBy=docker.service
```

#### 4.3、启动flannel

```
systemctl daemon-reload && systemctl start flanneld
```



### 5、配置master节点

#### 5.1、拷贝证书

```
scp apiserver.key ${IP_ADDR}:/etc/kubernetes/ssl/
scp apiserver.pem ${IP_ADDR}:/etc/kubernetes/ssl/
scp kubelet_${IP_ADDR}.key ${IP_ADDR}:/etc/kubernetes/ssl/
scp kubelet_${IP_ADDR}.key ${IP_ADDR}:/etc/kubernetes/ssl/
```

#### 5.2、配置文件

##### 5.2.1、apiserver配置

```
# kubernetes system config
#
# The following values are used to configure the kube-apiserver
#

# The address on the local server to listen to.
KUBE_API_ADDRESS="--bind-address=172.16.70.65 --insecure-bind-address=172.16.70.65"

# The port on the local server to listen on.
KUBE_API_PORT="--secure-port=6443"

# Port minions listen on
# KUBELET_PORT="--kubelet-port=10250"

# Comma separated list of nodes in the etcd cluster
KUBE_ETCD_SERVERS="--etcd-servers=https://172.16.71.8:2379,https://172.16.71.9:2379,https://172.16.71.10:2379"

# Address range to use for services
KUBE_SERVICE_ADDRESSES="--service-cluster-ip-range=10.64.0.0/12"

# default admission control policies
KUBE_ADMISSION_CONTROL="--enable-admission-plugins=NamespaceLifecycle,LimitRanger,ServiceAccount,DefaultStorageClass,ResourceQuota"

# Add your own!
KUBE_API_ARGS="--allow-privileged=true \
               --service-account-key-file=/etc/kubernetes/ssl/apiserver.key \
               --tls-cert-file=/etc/kubernetes/ssl/apiserver.pem \
               --tls-private-key-file=/etc/kubernetes/ssl/apiserver.key \
               --client-ca-file=/etc/kubernetes/ssl/ca.pem \
               --etcd-cafile=/etc/kubernetes/ssl/ca.pem \
               --etcd-certfile=/etc/kubernetes/ssl/flannel_172.16.70.65.pem \
               --etcd-keyfile=/etc/kubernetes/ssl/flannel_172.16.70.65.key \
               --token-auth-file=/etc/kubernetes/token.csv \
               --authorization-mode=RBAC \
               --kubelet-https=true \
               --apiserver-count=5 \
               --default-not-ready-toleration-seconds=10 \
               --default-unreachable-toleration-seconds=10 \
               --delete-collection-workers=3 \
               --audit-log-maxage=30 \
	       --audit-log-maxbackup=3 \
	       --audit-log-maxsize=100 \
	       --event-ttl=1h \
               --enable-bootstrap-token-auth"
```

- 对应配置信息请修改对应节点信息

##### 5.2.2、controller-manager配置

```
# The following values are used to configure the kubernetes controller-manager

# defaults from config and apiserver should be adequate

# Add your own!
KUBE_CONTROLLER_MANAGER_ARGS="\
    --master=https://172.16.70.65:6443 \
    --service-account-private-key-file=/etc/kubernetes/ssl/apiserver.key \
    --root-ca-file=/etc/kubernetes/ssl/ca.pem \
    --allocate-node-cidrs=true \
    --cluster-name=kubernetes \
    --cluster-signing-cert-file=/etc/kubernetes/ssl/apiserver.pem \
    --cluster-signing-key-file=/etc/kubernetes/ssl/apiserver.key \
    --leader-elect=true \
    --cluster-cidr=10.80.0.0/12 \
    --service-cluster-ip-range=10.64.0.0/12 \
    --secure-port=10253 \
    --node-monitor-period=2s \
    --node-monitor-grace-period=16s \
    --pod-eviction-timeout=30s \
    --kubeconfig=/etc/kubernetes/kubelet.kubeconfig"
```

- 对应配置信息请修改对应节点信息

##### 5.2.3、scheduler配置

```
# kubernetes scheduler config

# default config should be adequate

# Add your own!
KUBE_SCHEDULER_ARGS="\
    --master=https://172.16.70.65:6443 \
    --kubeconfig=/etc/kubernetes/kubelet.kubeconfig \
    --leader-elect=true"
```

##### 5.2.4、config配置

```
# kubernetes system config
#
# The following values are used to configure various aspects of all
# kubernetes services, including
#
#   kube-apiserver.service
#   kube-controller-manager.service
#   kube-scheduler.service
#   kubelet.service
#   kube-proxy.service
# logging to stderr means we get it in the systemd journal
KUBE_LOGTOSTDERR="--logtostderr=true"

# journal message level, 0 is debug
KUBE_LOG_LEVEL="--v=3"

# Should this cluster be allowed to run privileged docker containers
KUBE_ALLOW_PRIV="--allow-privileged=true"

# How the controller-manager, scheduler, and proxy find the apiserver
#KUBE_MASTER="--master=https://apiserver.msfar.cn:6443
```

- 对应配置信息请修改对应节点信息
- 注释选项已经在新版本中弃用



#### 5.4、生成token和kubeconfig

##### 5.4.1、生成TLS Bootstrapping Token

```
export KUBE_APISERVER="https://apiserver.msfar.cn:6443"
export BOOTSTRAP_TOKEN=$(head -c 16 /dev/urandom | od -An -t x | tr -d ' ')
echo "Tokne: ${BOOTSTRAP_TOKEN}"

cat > token.csv <<EOF
${BOOTSTRAP_TOKEN},kubelet-bootstrap,10001,"system:kubelet-bootstrap"
EOF
```

#####5.4.2、创建 kubelet bootstrapping kubeconfig 文件

注：${KUBE_APISERVER}为HA地址，如是slb等服务，负载均衡后端服务器不能访问负载均衡地址，可以改为本机地址。建议使用haproxy做代理。

设置集群参数

```
kubectl config set-cluster kubernetes \
  --certificate-authority=/etc/kubernetes/ssl/ca.pem \
  --embed-certs=true \
  --server=${KUBE_APISERVER} \
  --kubeconfig=bootstrap.kubeconfig
```

设置客户端认证参数

```
kubectl config set-credentials kubelet-bootstrap \
  --token=${BOOTSTRAP_TOKEN} \
  --kubeconfig=bootstrap.kubeconfig
```

设置上下文参数

```
kubectl config set-context default \
  --cluster=kubernetes \
  --user=kubelet-bootstrap \
  --kubeconfig=bootstrap.kubeconfig
```

设置默认上下文

```
kubectl config use-context default --kubeconfig=bootstrap.kubeconfig
```

#####5.4.3、创建 kubectl kubeconfig 文件

设置集群参数

```
kubectl config set-cluster kubernetes \
  --certificate-authority=/etc/kubernetes/ssl/ca.pem \
  --server=${KUBE_APISERVER}
```

设置客户端认证参数

```
kubectl config set-credentials admin \
  --client-certificate=/etc/kubernetes/ssl/kubelet_${IP_ADDR}.pem \
  --client-key=/etc/kubernetes/ssl/kubelet_${IP_ADDR}.key
```

设置上下文参数

```
kubectl config set-context kubernetes \
  --cluster=kubernetes \
  --user=admin
```

设置默认上下文

```
kubectl config use-context kubernetes
```

- kubelet.pem 证书的OU字段值为system:masters，kube-apiserver预定义的RoleBinding cluster-admin 将 Group system:masters 与 Role cluster-admin 绑定，该Role授予了调用kube-apiserver相关API的权限
- 生成的kubeconfig被保存到~/.kube/config文件

####5.4.4、创建 kubelet kubeconfig 文件

设置集群参数

```
kubectl config set-cluster kubernetes \
  --certificate-authority=/etc/kubernetes/ssl/ca.pem \
  --server=${KUBE_APISERVER} \
  --kubeconfig=kubelet.kubeconfig
```

设置客户端认证参数

```
kubectl config set-credentials kubelet \
  --client-certificate=/etc/kubernetes/ssl/kubelet_${IP_ADDR}.pem \
  --client-key=/etc/kubernetes/ssl/kubelet_${IP_ADDR}.key \
  --kubeconfig=kubelet.kubeconfig
```

生成上下文参数

```
kubectl config set-context default \
  --cluster=kubernetes \
  --user=kubelet \
  --kubeconfig=kubelet.kubeconfig
```

切换默认上下文

```
kubectl config use-context default --kubeconfig=kubelet.kubeconfig
```

#####5.4.5、创建 kube-proxy kubeconfig 文件

设置集群参数

```
kubectl config set-cluster kubernetes \
  --certificate-authority=/etc/kubernetes/ssl/ca.pem \
  --embed-certs=true \
  --server=${KUBE_APISERVER} \
  --kubeconfig=kube-proxy.kubeconfig
```

设置客户端认证参数

```
kubectl config set-credentials kube-proxy \
  --client-certificate=/etc/kubernetes/ssl/kube-proxy_${IP_ADDR}.pem \
  --client-key=/etc/kubernetes/ssl/kube-proxy__${IP_ADDR}.key \
  --embed-certs=true \
  --kubeconfig=kube-proxy.kubeconfig
```

设置上下文参数

```
kubectl config set-context default \
  --cluster=kubernetes \
  --user=kube-proxy \
  --kubeconfig=kube-proxy.kubeconfig
```

设置默认上下文

```
kubectl config use-context default --kubeconfig=kube-proxy.kubeconfig
```

- --embed-cert 都为 true，这会将certificate-authority、client-certificate和client-key指向的证书文件内容写入到生成的kube-proxy.kubeconfig文件中
- kube-proxy.pem证书中CN为system:kube-proxy，kube-apiserver预定义的 RoleBinding cluster-admin将User system:kube-proxy与Role system:node-proxier绑定，该Role授予了调用kube-apiserver Proxy相关API的权限

##### 5.4.6、将token文件和kubeconfig 文件拷贝至对应节点

```
scp token.csv ${master}:/etc/kubernetes/
scp bootstrapping.kubeconfig ${master}:/etc/kubernetes/
scp kubelet.kubeconfig ${master}:/etc/kubernetes/
```



### 6、配置node节点

#### 6.1、拷贝证书

```
scp kubelet_${IP_ADDR}.key ${IP_ADDR}:/etc/kubernetes/ssl/
scp kubelet_${IP_ADDR}.pem ${IP_ADDR}:/etc/kubernetes/ssl/
scp kube-proxy_${IP_ADDR}.key ${IP_ADDR}:/etc/kubernetes/ssl/
scp kube-proxy_${IP_ADDR}.pem ${IP_ADDR}:/etc/kubernetes/ssl/
```

#### 6.2、配置文件

##### 6.2.1、kubelet配置文件

```
## The address for the info server to serve on (set to 0.0.0.0 or "" for all interfaces)
KUBELET_ADDRESS="--address=172.16.70.161"
#
## The port for the info server to serve on
#KUBELET_PORT="--port=10250"
#
## You may leave this blank to use the actual hostname
KUBELET_HOSTNAME="--hostname-override=172.16.70.161"
#
## location of the api-server
## COMMENT THIS ON KUBERNETES 1.8+
#KUBELET_API_SERVER="--api-servers=https://registry.anymb.com:6443"
#
## pod infrastructure container
KUBELET_POD_INFRA_CONTAINER="--pod-infra-container-image=registry.anymb.com/library/pause-amd64:3.1"
#
## Add your own!
KUBELET_ARGS="--cgroup-driver=systemd \
              --cluster-dns=10.64.0.2 \
              --bootstrap-kubeconfig=/etc/kubernetes/bootstrap.kubeconfig \
              --kubeconfig=/etc/kubernetes/kubelet.kubeconfig  \
              --cert-dir=/etc/kubernetes/ssl \
              --cluster-domain=cluster.local \
              --hairpin-mode promiscuous-bridge \
              --serialize-image-pulls=false"
```

- 请将相关配置修改为对应节点配置

##### 6.2.2、proxy配置文件

```
# kubernetes proxy config

# default config should be adequate

# Add your own!
KUBE_PROXY_ARGS="--bind-address=172.16.70.161 \
                 --cluster-cidr=10.64.0.0/12 \
		         --masquerade-all \
		         --proxy-mode=ipvs \
		         --ipvs-min-sync-period=2s \
		         --ipvs-sync-period=3s \
		         --ipvs-scheduler=rr \
                 --kubeconfig=/etc/kubernetes/kube-proxy.kubeconfig"
```

- 请将相关配置修改为对应节点配置

#####6.2.3、config配置文件

```
# kubernetes system config
#
# The following values are used to configure various aspects of all
# kubernetes services, including
#
#   kube-apiserver.service
#   kube-controller-manager.service
#   kube-scheduler.service
#   kubelet.service
#   kube-proxy.service
# logging to stderr means we get it in the systemd journal
KUBE_LOGTOSTDERR="--logtostderr=true"

# journal message level, 0 is debug
KUBE_LOG_LEVEL="--v=3"

# Should this cluster be allowed to run privileged docker containers
KUBE_ALLOW_PRIV="--allow-privileged=true"

# How the controller-manager, scheduler, and proxy find the apiserver
#KUBE_MASTER="--master=https://apiserver.msfar.cn:6443
```

####6.3、将kubeconfig 文件拷贝至对应节点

```
scp bootstrapping.kubeconfig ${node}:/etc/kubernetes/
scp kubelet.kubeconfig ${node}:/etc/kubernetes/
scp kube-proxy.kubeconfig ${node}:/etc/kubernetes/
```

```
#创建kubelet数据目录
mkdir /data/data/kubelet
```

#### 6.4、设置权限

设置selinux规则

```
chcon -u system_u -t svirt_sandbox_file_t /data/data/kubelet
```

添加acl规则

```
setfacl -m u:kube:r /etc/kubernetes/*.kubeconfig
```



### 7、启动所有节点服务，验证服务

注意启动之前确认配置文件修改无误

####7.1、启动master节点服务

```
for master in {master01,master02,master03};do
    ssh ${master} "systemctl daemon-reload && systemctl start flanneld docker kube-apiserver kube-controller-manager kube-scheduler kubelet && systemctl enable flanneld docker kube-apiserver kube-controller-manager kube-scheduler kubelet "
done
```

####7.2、启动node节点服务

```
for node in {node01,node02,node03};do
    ssh ${node} "systemctl daemon-reload && systemctl start flanneld docker kubelet kube-proxy && systemctl enable flanneld docker kubelet kube-proxy"
done
```

####7.3、验证集群

```
# 在master机器上执行，授权kubelet-bootstrap角色
kubectl create clusterrolebinding kubelet-bootstrap \
  --clusterrole=system:node-bootstrapper \
  --user=kubelet-bootstrap

验证 master 节点功能
$ kubectl get componentstatuses
NAME                 STATUS    MESSAGE              ERROR
controller-manager   Healthy   ok
scheduler            Healthy   ok
etcd-2               Healthy   {"health": "true"}
etcd-0               Healthy   {"health": "true"}
etcd-1               Healthy   {"health": "true"}

#通过所有集群认证
kubectl get csr
kubectl get csr | awk '/Pending/ {print $1}' | xargs kubectl certificate approve

#检查node Ready
kubectl  get nodes 
NAME            STATUS    ROLES     AGE       VERSION
172.16.70.161   Ready     <none>    5h        v1.10.4
172.16.70.162   Ready     <none>    5h        v1.10.4
172.16.70.68    Ready     <none>    5h        v1.10.4


#添加kubectl命令补全
vim /etc/profile
source <(kubectl completion bash)
```



### 8、部署基础组件

#### 8.1、部署kube-router组件

```
#镜相下载：docker.io/cloudnativelabs/kube-router:latest
apiVersion: v1
kind: ConfigMap
metadata:
  name: kube-router-cfg
  namespace: kube-system
  labels:
    tier: node
    k8s-app: kube-router
data:
  cni-conf.json: |
    {
      "name":"kubernetes",
      "type":"bridge",
      "bridge":"kube-bridge",
      "isDefaultGateway":true,
      "ipam": {
        "type":"host-local"
      }
    }
---
apiVersion: extensions/v1beta1
kind: DaemonSet
metadata:
  labels:
    k8s-app: kube-router
    tier: node
  name: kube-router
  namespace: kube-system
spec:
  template:
    metadata:
      labels:
        k8s-app: kube-router
        tier: node
      annotations:
        scheduler.alpha.kubernetes.io/critical-pod: ''
    spec:
      serviceAccountName: kube-router
      serviceAccount: kube-router
      containers:
      - name: kube-router
        image: k8s-registry.local/public/kube-router:latest
        imagePullPolicy: Always
        args:
        - --run-router=true
        - --run-firewall=true
        - --run-service-proxy=true
        - --kubeconfig=/var/lib/kube-router/kubeconfig
        env:
        - name: NODE_NAME
          valueFrom:
            fieldRef:
              fieldPath: spec.nodeName
        resources:
          requests:
            cpu: 250m
            memory: 250Mi
        securityContext:
          privileged: true
        volumeMounts:
        - name: lib-modules
          mountPath: /lib/modules
          readOnly: true
        - name: cni-conf-dir
          mountPath: /etc/cni/net.d
        - name: kubeconfig
          mountPath: /var/lib/kube-router/kubeconfig
        - name: run
          mountPath: /var/run/docker.sock
          readOnly: true
      initContainers:
      - name: install-cni
        image: k8s-registry.local/public/busybox:latest
        imagePullPolicy: Always
        command:
        - /bin/sh
        - -c
        - set -e -x;
          if [ ! -f /etc/cni/net.d/10-kuberouter.conf ]; then
            TMP=/etc/cni/net.d/.tmp-kuberouter-cfg;
            cp /etc/kube-router/cni-conf.json ${TMP};
            mv ${TMP} /etc/cni/net.d/10-kuberouter.conf;
          fi
        volumeMounts:
        - name: cni-conf-dir
          mountPath: /etc/cni/net.d
        - name: kube-router-cfg
          mountPath: /etc/kube-router
      hostNetwork: true
      hostIPC: true
      hostPID: true
      tolerations:
      - key: CriticalAddonsOnly
        operator: Exists
      - effect: NoSchedule
        key: node-role.kubernetes.io/master
        operator: Exists
      volumes:
      - name: lib-modules
        hostPath:
          path: /lib/modules
      - name: cni-conf-dir
        hostPath:
          path: /etc/cni/net.d
      - name: run
        hostPath:
          path: /var/run/docker.sock
      - name: kube-router-cfg
        configMap:
          name: kube-router-cfg
      - name: kubeconfig
        hostPath:
          path: /etc/kubernetes/ssl/kubeconfig
       # configMap:
        #  name: kube-proxy
         # items:
         # - key: kubeconfig.conf
         #   path: kubeconfig
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: kube-router
  namespace: kube-system
---
kind: ClusterRole
apiVersion: rbac.authorization.k8s.io/v1beta1
metadata:
  name: kube-router
  namespace: kube-system
rules:
  - apiGroups:
    - ""
    resources:
      - namespaces
      - pods
      - services
      - nodes
      - endpoints
    verbs:
      - list
      - get
      - watch
  - apiGroups:
    - "networking.k8s.io"
    resources:
      - networkpolicies
    verbs:
      - list
      - get
      - watch
  - apiGroups:
    - extensions
    resources:
      - networkpolicies
    verbs:
      - get
      - list
      - watch
---
kind: ClusterRoleBinding
apiVersion: rbac.authorization.k8s.io/v1beta1
metadata:
  name: kube-router
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: kube-router
subjects:
- kind: ServiceAccount
  name: kube-router
  namespace: kube-system
------------------------------------------------------------
kubectl create -f kube-router.yaml
```

####8.2、部署kube-dashboard

```
# Example usage: kubectl create -f <this_file>

# ------------------- Dashboard Secret ------------------- #

apiVersion: v1
kind: Secret
metadata:
  labels:
    k8s-app: kubernetes-dashboard
  name: kubernetes-dashboard-certs
  namespace: kube-system
type: Opaque

---
# ------------------- Dashboard Service Account ------------------- #

apiVersion: v1
kind: ServiceAccount
metadata:
  labels:
    k8s-app: kubernetes-dashboard
  name: kubernetes-dashboard
  namespace: kube-system

---
# ------------------- Dashboard Role & Role Binding ------------------- #

kind: Role
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  name: kubernetes-dashboard-minimal
  namespace: kube-system
rules:
  # Allow Dashboard to create 'kubernetes-dashboard-key-holder' secret.
- apiGroups: [""]
  resources: ["secrets"]
  verbs: ["create"]
  # Allow Dashboard to create 'kubernetes-dashboard-settings' config map.
- apiGroups: [""]
  resources: ["configmaps"]
  verbs: ["create"]
  # Allow Dashboard to get, update and delete Dashboard exclusive secrets.
- apiGroups: [""]
  resources: ["secrets"]
  resourceNames: ["kubernetes-dashboard-key-holder", "kubernetes-dashboard-certs"]
  verbs: ["get", "update", "delete"]
  # Allow Dashboard to get and update 'kubernetes-dashboard-settings' config map.
- apiGroups: [""]
  resources: ["configmaps"]
  resourceNames: ["kubernetes-dashboard-settings"]
  verbs: ["get", "update"]
  # Allow Dashboard to get metrics from heapster.
- apiGroups: [""]
  resources: ["services"]
  resourceNames: ["heapster"]
  verbs: ["proxy"]
- apiGroups: [""]
  resources: ["services/proxy"]
  resourceNames: ["heapster", "http:heapster:", "https:heapster:"]
  verbs: ["get"]

---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: kubernetes-dashboard-minimal
  namespace: kube-system
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: kubernetes-dashboard-minimal
subjects:
- kind: ServiceAccount
  name: kubernetes-dashboard
  namespace: kube-system

---
# ------------------- Dashboard Deployment ------------------- #

kind: Deployment
apiVersion: apps/v1beta2
metadata:
  labels:
    k8s-app: kubernetes-dashboard
  name: kubernetes-dashboard
  namespace: kube-system
spec:
  replicas: 1
  revisionHistoryLimit: 10
  selector:
    matchLabels:
      k8s-app: kubernetes-dashboard
  template:
    metadata:
      labels:
        k8s-app: kubernetes-dashboard
    spec:
      #nodeSelector:
      #  role: master
      containers:
      - name: kubernetes-dashboard
        image: registry.anymb.com/library/kubernetes-dashboard-amd64:v1.8.3
        ports:
        - containerPort: 8443
          protocol: TCP
        args:
          - --auto-generate-certificates
          - --heapster-host=http://heapster
          # Uncomment the following line to manually specify Kubernetes API server Host
          # If not specified, Dashboard will attempt to auto discover the API server and connect
          # to it. Uncomment only if the default does not work.
        volumeMounts:
        - name: kubernetes-dashboard-certs
          mountPath: /certs
          # Create on-disk volume to store exec logs
        - mountPath: /tmp
          name: tmp-volume
        livenessProbe:
          httpGet:
            scheme: HTTPS
            path: /
            port: 8443
          initialDelaySeconds: 30
          timeoutSeconds: 30
      #imagePullSecrets:
      #- name: registry
      volumes:
      - name: kubernetes-dashboard-certs
        secret:
          secretName: kubernetes-dashboard-certs
      - name: tmp-volume
        emptyDir: {}
      serviceAccountName: kubernetes-dashboard
      # Comment the following tolerations if Dashboard must not be deployed on master
      tolerations:
      - key: node-role.kubernetes.io/master
        effect: NoSchedule

---
# ------------------- Dashboard Service ------------------- #

kind: Service
apiVersion: v1
metadata:
  labels:
    k8s-app: kubernetes-dashboard
  name: kubernetes-dashboard
  namespace: kube-system
spec:
  ports:
  - port: 8443
  selector:
    k8s-app: kubernetes-dashboard
```

```
kubectl create -f kubernetes-dashboard.yaml
```

绑定外部域名访问

```
apiVersion: extensions/v1beta1
kind: Ingress
metadata:
  name: kubernetes-dashboard
  namespace: kube-system
  annotations:
    nginx.ingress.kubernetes.io/secure-backends: "true"
spec:
  rules:
  - host: k8s.msfar.cn
    http:
      paths:
      - backend:
          serviceName: kubernetes-dashboard
          servicePort: 8443
```



#### 8.3、部署ingress

创建label,在创建ingress固定ingress所在节点

```
kubectl label no 172.16.70.61 role=ingress
kubectl label no 172.16.70.62 role=ingress
kubectl label no 172.16.70.63 role=ingress
```

```
kubectl get no --show-labels
```

启动ingress

```
---

apiVersion: v1
kind: Namespace
metadata:
  name: ingress-nginx
---

apiVersion: extensions/v1beta1
kind: Deployment
metadata:
  name: default-http-backend
  labels:
    app: default-http-backend
  namespace: ingress-nginx
spec:
  replicas: 1
  selector:
    matchLabels:
      app: default-http-backend
  template:
    metadata:
      labels:
        app: default-http-backend
    spec:
      nodeSelector:
        role: ingress
      terminationGracePeriodSeconds: 60
      containers:
      - name: default-http-backend
        # Any image is permissible as long as:
        # 1. It serves a 404 page at /
        # 2. It serves 200 on a /healthz endpoint
        image: registry.anymb.com/library/defaultbackend:1.4
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8080
            scheme: HTTP
          initialDelaySeconds: 30
          timeoutSeconds: 5
        ports:
        - containerPort: 8080
        resources:
          limits:
            cpu: 10m
            memory: 20Mi
          requests:
            cpu: 10m
            memory: 20Mi
---

apiVersion: v1
kind: Service
metadata:
  name: default-http-backend
  namespace: ingress-nginx
  labels:
    app: default-http-backend
spec:
  ports:
  - port: 80
    targetPort: 8080
  selector:
    app: default-http-backend
---

kind: ConfigMap
apiVersion: v1
metadata:
  name: nginx-configuration
  namespace: ingress-nginx
  labels:
    app: ingress-nginx
---

kind: ConfigMap
apiVersion: v1
metadata:
  name: tcp-services
  namespace: ingress-nginx
---

kind: ConfigMap
apiVersion: v1
metadata:
  name: udp-services
  namespace: ingress-nginx
---

apiVersion: v1
kind: ServiceAccount
metadata:
  name: nginx-ingress-serviceaccount
  namespace: ingress-nginx

---

apiVersion: rbac.authorization.k8s.io/v1beta1
kind: ClusterRole
metadata:
  name: nginx-ingress-clusterrole
rules:
  - apiGroups:
      - ""
    resources:
      - configmaps
      - endpoints
      - nodes
      - pods
      - secrets
    verbs:
      - list
      - watch
  - apiGroups:
      - ""
    resources:
      - nodes
    verbs:
      - get
  - apiGroups:
      - ""
    resources:
      - services
    verbs:
      - get
      - list
      - watch
  - apiGroups:
      - "extensions"
    resources:
      - ingresses
    verbs:
      - get
      - list
      - watch
  - apiGroups:
      - ""
    resources:
        - events
    verbs:
        - create
        - patch
  - apiGroups:
      - "extensions"
    resources:
      - ingresses/status
    verbs:
      - update

---

apiVersion: rbac.authorization.k8s.io/v1beta1
kind: Role
metadata:
  name: nginx-ingress-role
  namespace: ingress-nginx
rules:
  - apiGroups:
      - ""
    resources:
      - configmaps
      - pods
      - secrets
      - namespaces
    verbs:
      - get
  - apiGroups:
      - ""
    resources:
      - configmaps
    resourceNames:
      # Defaults to "<election-id>-<ingress-class>"
      # Here: "<ingress-controller-leader>-<nginx>"
      # This has to be adapted if you change either parameter
      # when launching the nginx-ingress-controller.
      - "ingress-controller-leader-nginx"
    verbs:
      - get
      - update
  - apiGroups:
      - ""
    resources:
      - configmaps
    verbs:
      - create
  - apiGroups:
      - ""
    resources:
      - endpoints
    verbs:
      - get

---

apiVersion: rbac.authorization.k8s.io/v1beta1
kind: RoleBinding
metadata:
  name: nginx-ingress-role-nisa-binding
  namespace: ingress-nginx
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: nginx-ingress-role
subjects:
  - kind: ServiceAccount
    name: nginx-ingress-serviceaccount
    namespace: ingress-nginx

---

apiVersion: rbac.authorization.k8s.io/v1beta1
kind: ClusterRoleBinding
metadata:
  name: nginx-ingress-clusterrole-nisa-binding
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: nginx-ingress-clusterrole
subjects:
  - kind: ServiceAccount
    name: nginx-ingress-serviceaccount
    namespace: ingress-nginx
---

apiVersion: extensions/v1beta1
kind: Deployment
metadata:
  name: nginx-ingress-controller
  namespace: ingress-nginx
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ingress-nginx
  template:
    metadata:
      labels:
        app: ingress-nginx
      annotations:
        prometheus.io/port: '10254'
        prometheus.io/scrape: 'true'
    spec:
      nodeSelector:
        role: ingress
      serviceAccountName: nginx-ingress-serviceaccount
      containers:
        - name: nginx-ingress-controller
          image: registry.anymb.com/library/nginx-ingress-controller:0.15.0
          args:
            - /nginx-ingress-controller
            - --default-backend-service=$(POD_NAMESPACE)/default-http-backend
            - --configmap=$(POD_NAMESPACE)/nginx-configuration
            - --tcp-services-configmap=$(POD_NAMESPACE)/tcp-services
            - --udp-services-configmap=$(POD_NAMESPACE)/udp-services
            - --publish-service=$(POD_NAMESPACE)/ingress-nginx
            - --annotations-prefix=nginx.ingress.kubernetes.io
          env:
            - name: POD_NAME
              valueFrom:
                fieldRef:
                  fieldPath: metadata.name
            - name: POD_NAMESPACE
              valueFrom:
                fieldRef:
                  fieldPath: metadata.namespace
          ports:
          - name: http
            containerPort: 80
          - name: https
            containerPort: 443
          livenessProbe:
            failureThreshold: 3
            httpGet:
              path: /healthz
              port: 10254
              scheme: HTTP
            initialDelaySeconds: 10
            periodSeconds: 10
            successThreshold: 1
            timeoutSeconds: 1
          readinessProbe:
            failureThreshold: 3
            httpGet:
              path: /healthz
              port: 10254
              scheme: HTTP
            periodSeconds: 10
            successThreshold: 1
            timeoutSeconds: 1
          securityContext:
            runAsNonRoot: false
```

```
kubectl create -f mandatory.yaml
```

创建ingress服务(nodePort允许的端口范围30000-32767)

```
apiVersion: v1
kind: Service
metadata:
  name: ingress-nginx
  namespace: ingress-nginx
spec:
  type: NodePort
  ports:
  - name: http
    port: 80
    targetPort: 80
    nodePort: 30080
    protocol: TCP
  - name: https
    port: 443
    targetPort: 443
    nodePort: 30443
    protocol: TCP
  selector:
    app: ingress-nginx
```



####8.4、部署coredns

```
apiVersion: v1
kind: ServiceAccount
metadata:
  name: coredns
  namespace: kube-system
  labels:
      kubernetes.io/cluster-service: "true"
      addonmanager.kubernetes.io/mode: Reconcile
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  labels:
    kubernetes.io/bootstrapping: rbac-defaults
    addonmanager.kubernetes.io/mode: Reconcile
  name: system:coredns
rules:
- apiGroups:
  - ""
  resources:
  - endpoints
  - services
  - pods
  - namespaces
  verbs:
  - list
  - watch
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  annotations:
    rbac.authorization.kubernetes.io/autoupdate: "true"
  labels:
    kubernetes.io/bootstrapping: rbac-defaults
    addonmanager.kubernetes.io/mode: EnsureExists
  name: system:coredns
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: system:coredns
subjects:
- kind: ServiceAccount
  name: coredns
  namespace: kube-system
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: coredns
  namespace: kube-system
  labels:
      addonmanager.kubernetes.io/mode: EnsureExists
data:
  Corefile: |
    .:53 {
        errors
        health
        kubernetes cluster.local. in-addr.arpa ip6.arpa {
            pods insecure
            upstream
            fallthrough in-addr.arpa ip6.arpa
        }
        prometheus :9153
        proxy . /etc/resolv.conf
        cache 30
    }
---
apiVersion: extensions/v1beta1
kind: Deployment
metadata:
  name: coredns
  namespace: kube-system
  labels:
    k8s-app: coredns
    kubernetes.io/cluster-service: "true"
    addonmanager.kubernetes.io/mode: Reconcile
    kubernetes.io/name: "CoreDNS"
spec:
  replicas: 4
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
  selector:
    matchLabels:
      k8s-app: coredns
  template:
    metadata:
      labels:
        k8s-app: coredns
    spec:
      serviceAccountName: coredns
      tolerations:
        - key: node-role.kubernetes.io/master
          effect: NoSchedule
        - key: "CriticalAddonsOnly"
          operator: "Exists"
      containers:
      - name: coredns
        image: coredns/coredns:1.0.6
        imagePullPolicy: IfNotPresent
        resources:
          limits:
            memory: 170Mi
          requests:
            cpu: 100m
            memory: 70Mi
        args: [ "-conf", "/etc/coredns/Corefile" ]
        volumeMounts:
        - name: config-volume
          mountPath: /etc/coredns
        ports:
        - containerPort: 53
          name: dns
          protocol: UDP
        - containerPort: 53
          name: dns-tcp
          protocol: TCP
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
            scheme: HTTP
          initialDelaySeconds: 60
          timeoutSeconds: 5
          successThreshold: 1
          failureThreshold: 5
      dnsPolicy: Default
      volumes:
        - name: config-volume
          configMap:
            name: coredns
            items:
            - key: Corefile
              path: Corefile
---
apiVersion: v1
kind: Service
metadata:
  name: coredns
  namespace: kube-system
  labels:
    k8s-app: coredns
    kubernetes.io/cluster-service: "true"
    addonmanager.kubernetes.io/mode: Reconcile
    kubernetes.io/name: "CoreDNS"
spec:
  selector:
    k8s-app: coredns
  clusterIP: 10.64.0.2
  ports:
  - name: dns
    port: 53
    protocol: UDP
  - name: dns-tcp
    port: 53
    protocol: TCP
```

```
kubectl create -f codedns.yaml
```

 

#### 8.5、部署dashboard

vim dashboard.yaml

```
# cat dashboard.yaml
# Copyright 2017 The Kubernetes Authors.
#
# Example usage: kubectl create -f <this_file>
# ------------------- Dashboard Secret ------------------- #

apiVersion: v1
kind: Secret
metadata:
  labels:
    k8s-app: kubernetes-dashboard
  name: kubernetes-dashboard-certs
  namespace: kube-system
type: Opaque

---
# ------------------- Dashboard Service Account ------------------- #

apiVersion: v1
kind: ServiceAccount
metadata:
  labels:
    k8s-app: kubernetes-dashboard
  name: kubernetes-dashboard
  namespace: kube-system

---
# ------------------- Dashboard Role & Role Binding ------------------- #

kind: Role
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  name: kubernetes-dashboard-minimal
  namespace: kube-system
rules:
  # Allow Dashboard to create 'kubernetes-dashboard-key-holder' secret.
- apiGroups: [""]
  resources: ["secrets"]
  verbs: ["create"]
  # Allow Dashboard to create 'kubernetes-dashboard-settings' config map.
- apiGroups: [""]
  resources: ["configmaps"]
  verbs: ["create"]
  # Allow Dashboard to get, update and delete Dashboard exclusive secrets.
- apiGroups: [""]
  resources: ["secrets"]
  resourceNames: ["kubernetes-dashboard-key-holder", "kubernetes-dashboard-certs"]
  verbs: ["get", "update", "delete"]
  # Allow Dashboard to get and update 'kubernetes-dashboard-settings' config map.
- apiGroups: [""]
  resources: ["configmaps"]
  resourceNames: ["kubernetes-dashboard-settings"]
  verbs: ["get", "update"]
  # Allow Dashboard to get metrics from heapster.
- apiGroups: [""]
  resources: ["services"]
  resourceNames: ["heapster"]
  verbs: ["proxy"]
- apiGroups: [""]
  resources: ["services/proxy"]
  resourceNames: ["heapster", "http:heapster:", "https:heapster:"]
  verbs: ["get"]

---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: kubernetes-dashboard-minimal
  namespace: kube-system
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: kubernetes-dashboard-minimal
subjects:
- kind: ServiceAccount
  name: kubernetes-dashboard
  namespace: kube-system

---
# ------------------- Dashboard Deployment ------------------- #

kind: Deployment
apiVersion: apps/v1beta2
metadata:
  labels:
    k8s-app: kubernetes-dashboard
  name: kubernetes-dashboard
  namespace: kube-system
spec:
  replicas: 1
  revisionHistoryLimit: 10
  selector:
    matchLabels:
      k8s-app: kubernetes-dashboard
  template:
    metadata:
      labels:
        k8s-app: kubernetes-dashboard
    spec:
      #nodeSelector:
      #  role: master
      containers:
      - name: kubernetes-dashboard
        image: registry.anymb.com/library/kubernetes-dashboard-amd64:v1.8.3
        ports:
        - containerPort: 8443
          protocol: TCP
        args:
          - --auto-generate-certificates
          - --heapster-host=http://heapster
          # Uncomment the following line to manually specify Kubernetes API server Host
          # If not specified, Dashboard will attempt to auto discover the API server and connect
          # to it. Uncomment only if the default does not work.
        volumeMounts:
        - name: kubernetes-dashboard-certs
          mountPath: /certs
          # Create on-disk volume to store exec logs
        - mountPath: /tmp
          name: tmp-volume
        livenessProbe:
          httpGet:
            scheme: HTTPS
            path: /
            port: 8443
          initialDelaySeconds: 30
          timeoutSeconds: 30
      volumes:
      - name: kubernetes-dashboard-certs
        secret:
          secretName: kubernetes-dashboard-certs
      - name: tmp-volume
        emptyDir: {}
      serviceAccountName: kubernetes-dashboard
      # Comment the following tolerations if Dashboard must not be deployed on master
      tolerations:
      - key: node-role.kubernetes.io/master
        effect: NoSchedule

---
# ------------------- Dashboard Service ------------------- #

kind: Service
apiVersion: v1
metadata:
  labels:
    k8s-app: kubernetes-dashboard
  name: kubernetes-dashboard
  namespace: kube-system
spec:
  ports:
  - port: 8443
    targetPort: 8443
  selector:
    k8s-app: kubernetes-dashboard
```

vim admin.yaml

```
apiVersion: v1
kind: ServiceAccount
metadata:
  name: admin-masonglin
  namespace: kube-system

---
apiVersion: rbac.authorization.k8s.io/v1beta1
kind: ClusterRoleBinding
metadata:
  name: admin-masonglin
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-admin
subjects:
- kind: ServiceAccount
  name: admin-masonglin
  namespace: kube-system
```

vim ingress.yaml

```
apiVersion: extensions/v1beta1
kind: Ingress
metadata:
  name: kubernetes-dashboard
  namespace: kube-system
  annotations:
    nginx.ingress.kubernetes.io/secure-backends: "true"
spec:
  rules:
  - host: k8s.msfar.cn
    http:
      paths:
      - backend:
          serviceName: kubernetes-dashboard
          servicePort: 8443
```
vim heapster.yaml
```
apiVersion: v1
kind: ServiceAccount
metadata:
  name: heapster
  namespace: kube-system
---
apiVersion: extensions/v1beta1
kind: Deployment
metadata:
  name: heapster
  namespace: kube-system
spec:
  replicas: 1
  template:
    metadata:
      labels:
        task: monitoring
        k8s-app: heapster
    spec:
      serviceAccountName: heapster
      containers:
      - name: heapster
        image: registry.anymb.com/library/heapster-amd64:v1.5.3
        imagePullPolicy: IfNotPresent
        command:
        - /heapster
        - --source=kubernetes:https://kubernetes.default
---
apiVersion: v1
kind: Service
metadata:
  labels:
    task: monitor
    # For use as a Cluster add-on (https://github.com/kubernetes/kubernetes/tree/master/cluster/addons)
    # If you are NOT using this as an addon, you should comment out this line.
    kubernetes.io/cluster-service: 'true'
    kubernetes.io/name: Heapster
  name: heapster
  namespace: kube-system
spec:
  ports:
  - port: 80
    targetPort: 8082
  selector:
    k8s-app: heapster
```

```
kubectl create -f .
```



#### 8.6、启用HPA

##### 8.6.1、编辑apiserver

编辑/etc/kubernetes/apiserver，添加以下配置：

```
               --requestheader-client-ca-file=/etc/kubernetes/ssl/ca.pem \
               --proxy-client-cert-file=/etc/kubernetes/ssl/kubelet_172.17.15.242.pem \
               --proxy-client-key-file=/etc/kubernetes/ssl/kubelet_172.17.15.242.key \
               --requestheader-allowed-names=admin \
               --requestheader-extra-headers-prefix=X-Remote-Extra- \
               --requestheader-group-headers=X-Remote-Group \
               --requestheader-username-headers=X-Remote-User \
               --enable-aggregator-routing=true \
               --max-requests-inflight=3000 \
```

- --requestheader-client-ca-file **使用集群CA证书**
- --proxy-client-cert-file **使用kubelet 证书**
- --proxy-client-key-file **使用kubelet key**
- --requestheader-allowed-names **设置为 admin**, 与 kubelet 证书 CN 字段相同

      注：如不相同会以下错误：x509:subject with cn=admin is not in the allowed list: [aggregator]

- --enable-aggregator-routing=true **在apiserver节点未运行kube-proxy，则需要启用该参数**



##### 8.6.2、重启apiserver

```
systemctl restart kube-apiserver
```

##### 8.6.3、创建Metrics Server

```
git clone https://github.com/kubernetes-incubator/metrics-server
cd metrics-server
kubectl create -f deploy/1.8+/
```

注：需修改metrics-server-deployment.yaml中image为自己镜像仓库中image

#####8.6.4、检查metice server状态

```
kubectl -n kube-system get pods -l k8s-app=metrics-server
```

##### 8.6.5、创建HPA

vim hpa.yaml

```
apiVersion: autoscaling/v1
kind: HorizontalPodAutoscaler
metadata:
  name: hpa-demo-service
  labels:
    app: demo-service
    label: hpa
spec:
  scaleTargetRef:
    apiVersion: v1
    kind: Deployment
    name: demo-service
  minReplicas: 1
  maxReplicas: 10
  targetCPUUtilizationPercentage: 30
```

vim deployment.yaml

```
apiVersion: apps/v1
kind: Deployment
metadata:
  name: demo-service
  labels:
    label: hpa
spec:
  replicas: 1
  selector:
    matchLabels:
      app: demo-service
      label: hpa
  template:
    metadata:
      labels:
        label: hpa
        app: demo-service
    spec:
      containers:
      - name: demo-service
        image: demo-image
        imagePullPolicy: Always
        securityContext:
          runAsUser:  1000
          privileged: true
        ports:
        - containerPort: 8080
        resources:
          limits:
            cpu: 600m
            memory: 2Gi
          requests:
            cpu: 300m
            memory: 1Gi
```

- resources.request必须设置

vim service.yaml

```
apiVersion: v1
kind: Service
metadata:
  name: demo-service
  labels:
    app: demo-service
    label: hpa

spec:
  ports:
  - port: 8080
  selector:
    app: demo-service
    label: hpa
```

```
kubectl create -f .
```

或者

```
kubectl autoscale deployment coredns --cpu-percent=60 --min=4 --max=10 -n kube-system
```



##### 8.6.6、CPU压力测试

```
time echo "scale=5000;4*a(1)" | bc -l -q
```



##### 8.6.7、配置jenkins发布

######8.6.7.1、为jenkins生成证书
vim name=jenkins

```
[ req ]
req_extensions = v3_req
distinguished_name = req_distinguished_name
[req_distinguished_name]
[ v3_req ]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
subjectAltName = @alt_names
[alt_names]
IP.1 = 172.16.63.3  #填写jenkins节点IP
```
```
name=jenkins
conf=jenkins.cnf

openssl genrsa -out $name.key 3072
openssl req -new -key $name.key -out $name.csr -subj "/CN=jenkins/OU=System/C=CN/ST=Shanghai/L=Shanghai/O=k8s"  -config $conf
openssl x509 -req -CA ca.pem -CAkey ca.key -CAcreateserial -in $name.csr -out $name.pem -days 1095 -extfile $conf -extensions v3_req
```

###### 8.6.7.2、配置jenkins agent

在jenkins中添加节点，具体操作不再叙述。

配置config文件，将前面生成的证书，以及ca证书放在同一目录

```
apiVersion: v1
clusters:
- cluster:
    certificate-authority: ca.pem
    server: https://apiserver.msfar.cn:6443
  name: kubernetes
contexts:
- context:
    cluster: kubernetes
    user: kubelet
  name: default
current-context: default
kind: Config
preferences: {}
users:
- name: kubelet
  user:
    client-certificate: jenkins_172.16.63.3.pem
    client-key: jenkins_172.16.63.3.key
```

修改脚本相关信息

```
#! /bin/bash

   name="k8s"
 secret="eb399171ad65d7201d8d640e56f4368c706c31a1d23427"
    url="https://jenkins.msfar.cn/computer/$name/slave-agent.jnlp"
   args="-Xmx32g -Xms32g"
dir_jks="/data/jenkins"
dir_lib="$dir_jks/lib"

if [ "`whoami`" = "root" ]
then
    su_cmd="su - jenkins -s /bin/sh -c"
fi

$su_cmd "java -jar $args $dir_lib/agent.jar -jnlpUrl $url -secret $secret -workDir $dir_jks/home"
```

运行agent容器

```
docker run -d -e ENV_NAME=k8s -v /data/jenkins:/data/jenkins -v /data/jenkins/files/k8s/k8s:/home/jenkins/.kube --name k8s registry.anymb.com/library/jenkins-agent:k8s-1.10.4
```

###### 8.6.7.2、配置k8s权限

根据不同namespace配置不同权限

```
kind: Role
apiVersion: rbac.authorization.k8s.io/v1beta1
metadata:
  namespace: NS
  name: jenkins
rules:
- apiGroups: [""]
  resources: ["pods", "services", "replicationcontrollers", "configmaps"]
  verbs:     ["get", "watch", "list", "create", "delete", "patch"]
- apiGroups: ["extensions", "apps"]
  resources: ["deployments", "replicasets", "statefulsets", "ingresses", "update"]
  verbs:     ["get", "watch", "list", "create", "delete", "patch", "update"]
- apiGroups: ["batch"]
  resources: ["cronjobs", "jobs"]
  verbs:     ["get", "watch", "list", "create", "delete", "patch", "update"]
- apiGroups: ["autoscaling"]
  resources: ["horizontalpodautoscalers"]
  verbs:     ["get", "watch", "list", "create", "delete", "patch", "update"]
---
kind: RoleBinding
apiVersion: rbac.authorization.k8s.io/v1beta1
metadata:
  name: jenkins
  namespace: NS
subjects:
- kind: User
  name: jenkins
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: jenkins
  apiGroup: rbac.authorization.k8s.io
```

##### 8.6.8、配置traefik

vim traefik.cnf

```
[req] 
distinguished_name = req_distinguished_name
prompt = yes

[ req_distinguished_name ]
countryName                     = Country Name (2 letter code)
countryName_value               = CN

stateOrProvinceName             = State or Province Name (full name)
stateOrProvinceName_value       = Shanghai

localityName                    = Locality Name (eg, city)
localityName_value              = Shanghai

organizationName                = Organization Name (eg, company)
organizationName_value          = anymb

organizationalUnitName          = Organizational Unit Name (eg, section)
organizationalUnitName_value    = anymb

commonName                      = Common Name (eg, your name or your server\'s hostname)
commonName_value                = *.multi.io


emailAddress                    = Email Address
emailAddress_value              = k8s@msfar.cn
```

生成证书

```
openssl req -newkey rsa:4096 -nodes -config traefik.cnf -days 3650 -x509 -out tls.crt -keyout tls.key
```

在k8s中创建secret

```
kubectl create -n kube-system secret tls ssl --cert tls.crt --key tls.key
```

创建traefik

```
kubectl create -f traefik.yml
```



