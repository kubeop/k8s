使用Ansible Playbook进行生产级别高可用kubernetes集群部署，包含初始化系统配置、自动签发集群证书、安装配置etcd集群、安装配置haproxy及keepalived、calico、coredns、metrics-server等，并使用bootstrap方式认证以及kubernetes组件健康检查。另外支持集群节点扩容、替换集群证书、kubernetes版本升级等。本Playbook使用二进制方式部署。

配合kubernetes剔除dockershim，本Playbook将运行时修改为containerd。

如需使用二进制方式一步一步安装，请参考[二进制安装kubernetes集群](https://www.k8sre.com/#/k8s/cluster/started)。



## 一、准备文件服务器

配置文件中指定的文件服务器下载比较慢，可以自行搭建kubernetes二进制文件的文件下载服务器。

### 1.1、下载二进制包

下载kubernetes

```
wget https://storage.googleapis.com/kubernetes-release/release/v1.20.4/kubernetes-server-linux-amd64.tar.gz
```

- url中v1.20.4替换为需要下载的版本即可。

下载cri-tools

```
wget https://github.com/kubernetes-sigs/cri-tools/releases/download/v1.20.0/crictl-v1.20.0-linux-amd64.tar.gz
```

- url中v1.20.4替换为需要下载的版本即可。

下载cni-plugins

```
wget https://github.com/containernetworking/plugins/releases/download/v0.8.7/cni-plugins-linux-amd64-v0.8.7.tgz
```

- url中v1.20.4替换为需要下载的版本即可。



### 1.2、配置文件服务器

安装nginx

```
yum -y install nginx
mkdir /usr/share/nginx/html/{cni-plugins,cri-tools,v1.20.4}
```

将文件拷贝nginx目录

```
# 解压
tar zxvf kubernetes-server-linux-amd64.tar.gz
# 拷贝kubernetes二进制文件到nginx目录
cp kubernetes/server/bin/{kube-apiserver,kube-controller-manager,kube-scheduler,kubectl,kubelet,kube-proxy} /usr/share/nginx/html/v1.20.4/
# 拷贝cri-tools文件到nginx目录
cp crictl-v1.20.0-linux-amd64.tar.gz /usr/share/nginx/html/cri-tools
# 拷贝cni-plugins文件到nginx目录
cp cni-plugins-linux-amd64-v0.8.7.tgz /usr/share/nginx/html/cni-plugins
```
启动服务
```
systemctl start nginx
```



## 二、配置Playbook

### 2.1、拉取Playbook代码

```
git clone https://github.com/k8sre/k8s.git
```



### 2.2、配置inventory

请按照inventory模板格式修改对应资源

```
#本组内填写etcd服务器及主机名
[etcd]
172.16.90.201 hostname=etcd-01
172.16.90.202 hostname=etcd-02
172.16.90.203 hostname=etcd-03

#本组内填写master服务器及主机名
[master]
172.16.90.204 hostname=master-01
172.16.90.205 hostname=master-02
172.16.90.206 hostname=master-03

[haproxy]
172.16.90.198 hostname=haproxy-01 type=MASTER priority=100
172.16.90.199 hostname=haproxy-02 type=BACKUP priority=90
[all:vars]
lb_port=6443
vip=172.16.90.200

#本组内填写node服务器及主机名
[node]
172.16.90.207 hostname=node-01
172.16.90.208 hostname=node-02
172.16.90.209 hostname=node-03
```

- 当haproxy和kube-apiserver部署在同一台服务器时，请将`lb_port`修改为其他不冲突的端口。



### 2.3、配置集群安装信息

编辑group_vars/all.yml文件，填入自己的配置。

请注意：

- 请尽量将etcd安装在独立的服务器上，不建议跟master安装在一起。数据盘尽量使用SSD盘。
- Pod 和Service IP网段建议使用保留私有IP段，建议（Pod IP不与Service IP重复，也不要与主机IP段重复，同时也避免与docker0网卡的网段冲突。）：
  - Pod 网段
    - A类地址：10.0.0.0/8
    - B类地址：172.16-31.0.0/12-16
    - C类地址：192.168.0.0/16
  - Service网段
    - A类地址：10.0.0.0/16-24
    - B类地址：172.16-31.0.0/16-24
    - C类地址：192.168.0.0/16-24



## 三、安装步骤

### 3.1、安装Ansible

在单独的Ansible控制机执行以下命令安装Ansible

```
yum -y install ansible
pip install netaddr -i https://mirrors.aliyun.com/pypi/simple/
```



### 3.2、格式化并挂载数据盘

如已经自行格式化并挂载目录完成，可以跳过此步骤。

etcd数据盘

```
ansible-playbook fdisk.yml -i inventory -l etcd -e "disk=sdb dir=/var/lib/etcd"
```

containerd数据盘

```
ansible-playbook fdisk.yml -i inventory -l master,node -e "disk=sdb dir=/var/lib/containerd"
```



### 3.3、部署集群

```
ansible-playbook k8s.yml -i inventory
```

- 成功执行结束后，既kubernetes集群部署成功。
- 后续部署其他基础插件可以参考[部署集群插件](https://www.k8sre.com/#/kubernetes/addons)。



如是公有云环境，使用公有云的负载均衡即可，无需安装haproxy和keepalived。另外，因公有云负载均衡不支持同时作为客户端和服务端，所以公有云负载均衡四层监听的后端服务器无法访问SLB。故做以下改造支持公有云环境：

```
#本组内填写master服务器及主机名
[master]
172.16.90.204 hostname=master-01 apiserver_domain_name=172.16.90.204
172.16.90.205 hostname=master-02 apiserver_domain_name=172.16.90.205
172.16.90.206 hostname=master-03 apiserver_domain_name=172.16.90.206
```

- 在inventory文件中，按照以上格式添加配置，将master节点连接的apiserver地址改为本机IP。

执行部署

```
ansible-playbook k8s.yml -i inventory --skip-tags=install_haproxy,install_keepalived
```

⚠️：默认使用calico ipip网络，部署成功后，可以自行修改。



## 四、扩容节点

### 4.1、扩容master节点

扩容时，请不要在inventory文件master组中保留旧服务器信息。

格式化挂载数据盘

```
ansible-playbook fdisk.yml -i inventory -l master -e "disk=sdb dir=/var/lib/containerd"
```

执行节点初始化

```
ansible-playbook k8s.yml -i inventory -l master -t init
```

执行节点扩容

```
ansible-playbook k8s.yml -i inventory -l master -t cert,install_master,install_containerd,install_node --skip-tags=bootstrap
```



### 4.2、扩容node节点

扩容时，请不要在inventory文件node组中保留旧服务器信息。

格式化挂载数据盘

```
ansible-playbook fdisk.yml -i inventory -l node -e "disk=sdb dir=/var/lib/containerd"
```

执行节点初始化

```
ansible-playbook k8s.yml -i inventory -l node -t init
```

执行节点扩容

```
ansible-playbook k8s.yml -i inventory -l node -t install_containerd,install_node,install_ceph --skip-tags=create_label
```



## 五、替换集群证书

先备份并删除证书目录{{ssl_dir}}，然后执行以下步骤重新生成证书并分发证书。

```
ansible-playbook k8s.yml -i inventory -t cert,dis_certs
```

然后依次重启每个节点。

重启etcd

```
ansible -i inventory etcd -m systemd -a "name=etcd state=restarted"
```

验证etcd

```
etcdctl \
  --endpoints=https://172.16.90.201:2379,https://172.16.90.202:2379,https://172.16.90.203:2379 \
  --cacert=/etc/kubernetes/pki/etcd-ca.pem \
  --cert=/etc/kubernetes/pki/etcd-client.pem \
  --key=/etc/kubernetes/pki/etcd-client.key \
  endpoint health 
```

逐个删除旧的kubelet证书

```
ansible -i inventory master,node -l master-01 -m shell -a "rm -rf /etc/kubernetes/pki/kubelet-*"
```

- `-l`参数更换为具体节点IP。

逐个重启节点

```
ansible-playbook k8s.yml -i inventory -l master-01 -t restart_apiserver,restart_controller,restart_scheduler,restart_kubelet,restart_proxy,healthcheck
```

- 如calico、metrics-server等服务也使用了etcd，请记得一起更新相关证书。
-  `-l`参数更换为具体节点IP。



## 六、升级kubernetes版本

请先将`kubernetes_url`修改为新版本下载链接。

安装kubernetes组件

```
ansible-playbook k8s.yml -i inventory -t kube_master,kube_node
```

然后依次重启每个kubernetes组件。

```
ansible-playbook k8s.yml -i inventory -l master-01 -t restart_apiserver,restart_controller,restart_scheduler,restart_kubelet,restart_proxy,healthcheck
```

- `-l`参数更换为具体节点IP。

