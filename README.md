使用Ansible Playbook进行生产级别高可用kubernetes集群部署，包含初始化系统配置、自动签发集群证书、安装配置etcd集群、安装配置haproxy及keepalived等，并使用bootstrap方式认证以及kubernetes组件健康检查。另外支持集群节点扩容、替换集群证书、kubernetes版本升级等。本Playbook使用二进制方式部署。



## 一、准备文件服务器

### 1.1、下载二进制包

```
wget https://storage.googleapis.com/kubernetes-release/release/v1.18.10/kubernetes-server-linux-amd64.tar.gz
```

- url中v1.18.10替换为需要下载的版本即可。



### 1.2、配置文件服务器

安装nginx

```
yum -y install nginx
```

将文件拷贝nginx目录

```
tar zxvf kubernetes-server-linux-amd64.tar.gz
cp kubernetes/server/bin/{kube-apiserver,kube-controller-manager,kube-scheduler,kubectl,kubelet,kube-proxy} /usr/share/nginx/html/
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



### 2.3、配置集群安装信息

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

- 请将etcd安装在独立的服务器上，不建议跟master安装在一起。数据盘尽量使用SSD盘。
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

在单独的Ansible机器或者master-01执行以下命令安装Ansible

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

docker数据盘

```
ansible-playbook fdisk.yml -i inventory -l master,node -e "disk=sdb dir=/var/lib/docker"
```



### 3.3、部署集群

```
ansible-playbook k8s.yml -i inventory
```

- 成功执行结束后，既kubernetes集群部署成功。
- 后续部署其他基础插件可以参考[部署集群插件](http://www.k8sre.com/#/kubernetes/2.1.binary?id=%e5%8d%81%e3%80%81%e9%83%a8%e7%bd%b2%e9%9b%86%e7%be%a4%e6%8f%92%e4%bb%b6)。



如是公有云环境，使用公有云的负载均衡即可，无需安装haproxy和keepalived。另外，因公有云负载均衡不支持同时作为客户端和服务端，所以公有云负载均衡四层监听的后端服务器无法访问SLB。故做以下改造支持公有云环境：

```
#本组内填写master服务器及主机名
[master]
172.16.100.204 hostname=master-01 apiserver_domain_name=172.16.100.204
172.16.100.205 hostname=master-02 apiserver_domain_name=172.16.100.205
172.16.100.206 hostname=master-03 apiserver_domain_name=172.16.100.206
```

- 在inventory文件中，按照以上格式添加配置，将master节点连接的apiserver地址改为本机IP。

执行部署

```
ansible-playbook k8s.yml -i inventory --skip-tags=install_haproxy,install_keepalived
```

⚠️：默认使用calico ipip网络，部署成功后，可以自行修改。



## 四、扩容节点

### 4.1、扩容master节点

扩容master前，请将{{ssl_dir}}目录中的kube-apiserver的证书备份并移除。

扩容时，请不要在inventory文件master组中保留旧服务器信息。

格式化挂载数据盘

```
ansible-playbook fdisk.yml -i inventory -l master -e "disk=sdb dir=/var/lib/docker"
```

执行节点初始化

```
ansible-playbook k8s.yml -i inventory -l master -t init
```

执行节点扩容

```
ansible-playbook k8s.yml -i inventory -l master -t cert,install_master,install_docker,install_node,install_ceph --skip-tags=bootstrap,cni
```



### 4.2、扩容node节点

扩容时，请不要在inventory文件node组中保留旧服务器信息。

格式化挂载数据盘

```
ansible-playbook fdisk.yml -i inventory -l node -e "disk=sdb dir=/var/lib/docker"
```

执行节点初始化

```
ansible-playbook k8s.yml -i inventory -l node -t init
```

执行节点扩容

```
ansible-playbook k8s.yml -i inventory -l node -t install_docker,install_node,install_ceph --skip-tags=create_label,cni
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

- `-l`参数更换为具体节点IP。

逐个重启节点

```
ansible-playbook k8s.yml -i inventory -l master-01 -t restart_apiserver,restart_controller,restart_scheduler,restart_kubelet,restart_proxy,healthcheck,approve_node
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

