本工具使用ansible playbook初始化系统配置、安装kubernetes高可用集群，并可进行节点扩容、替换集群证书等。本playbook安装kubernetes集群为二进制方式部署。



## 使用方法：

### 一、下载二进制包

```
wget https://storage.googleapis.com/kubernetes-release/release/v1.16.3/kubernetes-server-linux-amd64.tar.gz
```

- url中v1.16.3替换为需要下载的版本即可

配置文件服务器

```
yum -y install nginx
tar zxvf kubernetes-server-linux-amd64.tar.gz
cp kubernetes/server/bin/{kube-apiserver,kube-controller-manager,kube-scheduler,kubectl,kubelet,kube-proxy} /usr/share/nginx/html/
```

```
systemctl start nginx
```



### 二、准备资源

请按照inventory格式修改对应资源

```
#本组内填写etcd服务器及主机名
[etcd]
172.16.100.201 hostname=etcd-01
172.16.100.202 hostname=etcd-02
172.16.100.203 hostname=etcd-03

#本组内填写master服务器及主机名
[master]
172.16.100.204 hostname=master-01
172.16.100.205 hostname=master-02
172.16.100.206 hostname=master-03

[haproxy]
172.16.100.198 hostname=haproxy-01 type=MASTER priority=100
172.16.100.199 hostname=haproxy-02 type=BACKUP priority=90
[all:vars]
lb_port=6443
vip=172.16.100.200

#本组内填写node服务器及主机名
[node]
172.16.100.207 hostname=node-01
172.16.100.208 hostname=node-02
172.16.100.209 hostname=node-03
```

- 当haproxy和kube-apiserver部署在同一台服务器时，请将`lb_port`修改为其他不冲突的端口。



###  三、修改相关配置

编辑group_vars/all.yml文件，填入自己的配置

| 配置项                | 说明                                                         |
| --------------------- | ------------------------------------------------------------ |
| ssl_dir               | 签发ssl证书保存路径，ansible控制端机器上的路径。默认签发10年有效期的证书 |
| kubernetes_url        | kubernetes 二进制文件下载链接，请修改为自己的下载服务器地址  |
| docker_version        | 可通过查看版本yum list docker-ce --showduplicates\|sort -rn  |
| apiserver_domain_name | kube-apiserver的访问域名，需提前配置解析。不使用域名时，可以指定为负载均衡的IP（本Playbook需指定为haproxy的VIP） |
| service_ip_range      | 指定k8s集群service的网段                                     |
| pod_ip_range          | 指定k8s集群pod的网段                                         |
| calico_ipv4pool_ipip  | 指定k8s集群使用calico的ipip模式或者bgp模式，Always为ipip模式，off为bgp模式。注意bgp模式不适用于公有云环境。当值为off的时候，切记使用引号`""`引起来。 |

- 请将etcd安装在独立的服务器上，不建议跟master安装在一起
- Pod 和Service IP网段建议使用保留私有IP段，建议（Pod IP不与Service IP重复，也不要与主机IP段重复）：
  - Pod 网段
    - A类地址：10.0.0.0/8
    - B类地址：172.16-31.0.0/12-16
    - C类地址：192.168.0.0/16
  - Service网段
    - A类地址：10.0.0.0/16-24
    - B类地址：172.16-31.0.0/16-24
    - C类地址：192.168.0.0/16-24




### 四、使用方法

#### 4.1、安装ansible

在控制端机器执行以下命令安装ansible

```
yum -y install ansible
pip install netaddr
```



#### 4.2、部署集群

先执行格式化磁盘并挂载目录。如已经自行格式化磁盘并挂载，请跳过此步骤。

```
ansible-playbook fdisk.yml -i inventory -l etcd -e "disk=sdb dir=/var/lib/etcd"
ansible-playbook fdisk.yml -i inventory -l master,node -e "disk=sdb dir=/var/lib/docker"
```
安装k8s
```
ansible-playbook k8s.yml -i inventory
```

如是公有云环境，则执行：

```
ansible-playbook k8s.yml -i inventory --skip-tags=install_haproxy,install_keepalived
```

⚠️：默认使用calico ipip网络，部署成功后，可以自行修改。



#### 4.3、扩容mater节点

扩容master前，请将{{ssl_dir}}目录中的kube-apiserver的证书备份并移除。

扩容时，请不要在inventory文件master组中保留旧服务器信息。

```
ansible-playbook fdisk.yml -i inventory -l master -e "disk=sdb dir=/var/lib/docker"
ansible-playbook k8s.yml -i inventory -l master -t init
ansible-playbook k8s.yml -i inventory -l master -t cert,install_master,install_docker,install_node,install_ceph --skip-tags=bootstrap,cni
```



#### 4.4、扩容node节点

扩容时，请不要在inventory文件node组中保留旧服务器信息。

```
ansible-playbook fdisk.yml -i inventory -l node -e "disk=sdb dir=/var/lib/docker"
ansible-playbook k8s.yml -i inventory -l node -t init
ansible-playbook k8s.yml -i inventory -l node -t install_docker,install_node,install_ceph --skip-tags=create_label,cni
```



#### 4.5、替换集群证书

先备份并删除证书目录，然后执行以下步骤

```
ansible-playbook k8s.yml -i inventory -t cert
ansible-playbook k8s.yml -i inventory -t dis_certs
```

然后依次重启每个节点。

重启etcd

```
ansible -i inventory etcd -m systemd -a "name=etcd state=restarted"
```

验证etcd

```
ETCDCTL_API=3 etcdctl \
  --endpoints=https://172.16.100.201:2379,https://172.16.100.202:2379,https://172.16.100.203:2379 \
  --cacert=/etc/kubernetes/pki/etcd-ca.pem \
  --cert=/etc/kubernetes/pki/etcd-client.pem \
  --key=/etc/kubernetes/pki/etcd-client.key \
  endpoint health 
```

逐个删除旧的kubelet证书

```
ansible -i inventory master,node -l master-01 -m shell -a "rm -rf /etc/kubernetes/pki/kubelet-*"
```

- `-l`参数更换为具体节点IP

逐个重启节点

```
ansible-playbook k8s.yml -i inventory -l master-01 -t restart_apiserver,restart_controller,restart_scheduler,restart_kubelet,restart_proxy,healthcheck,approve_node
```

- 如calico、metrics-server等服务也使用了etcd，请记得一起更新相关证书。
-  `-l`参数更换为具体节点IP



#### 4.6、升级kubernetes版本

请先将`kubernetes_url`修改为新版本下载链接

```
ansible-playbook k8s.yml -i inventory -t kube_master,kube_node
```

然后依次重启每个kubernetes组件。

```
ansible-playbook k8s.yml -i inventory -l master-01 -t restart_apiserver,restart_controller,restart_scheduler,restart_kubelet,restart_proxy,healthcheck
```

- `-l`参数更换为具体节点IP

