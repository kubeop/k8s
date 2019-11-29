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
cd kubernetes/server/bin
cp {kube-apiserver,kube-controller-manager,kube-scheduler,kubectl,kubelet,kube-proxy} /usr/share/nginx/html/
```

```
systemctl start nginx
```



### 二、准备资源

请按照inventory格式修改对应资源

```
#本组内填写etcd服务器及主机名
[etcd]
10.10.100.201 hostname=etcd-01
10.10.100.202 hostname=etcd-02
10.10.100.203 hostname=etcd-03

#本组内填写master服务器及主机名
[master]
10.10.100.204 hostname=master-01
10.10.100.205 hostname=master-02
10.10.100.206 hostname=master-03

[haproxy]
10.10.100.198 hostname=haproxy-01 type=MASTER priority=100
10.10.100.199 hostname=haproxy-02 type=BACKUP priority=90
[all:vars]
vip=10.10.100.200

#本组内填写node服务器及主机名
[node]
10.10.100.207 hostname=node-01
10.10.100.208 hostname=node-02
10.10.100.209 hostname=node-03
```



###  三、修改相关配置

编辑group_vars/all.yml文件，填入自己的配置

| 配置项                | 说明                                                         |
| --------------------- | ------------------------------------------------------------ |
| ssl_dir               | 签发ssl证书保存路径，ansible控制端机器上的路径。默认签发10年有效期的证书 |
| kubernetes_url        | kubernetes 二进制文件下载链接                                |
| docker_version        | 可通过查看版本yum list docker-ce --showduplicates\|sort -rn  |
| apiserver_domain_name | kube-apiserver的访问域名，需提前配置解析。不使用域名时，可以指定为负载均衡的IP（本Playbook需指定为haproxy的VIP） |
| service_ip_range      | 指定k8s集群service的网段                                     |
| pod_ip_range          | 指定k8s集群pod的网段                                         |

- 请将etcd安装在独立的服务器上，不建议跟master安装在一起




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
ansible-playbook fdisk.yml -i inventory -l etcd -e "dir=/var/lib/etcd"
ansible-playbook fdisk.yml -i inventory -l master,node -e "dir=/var/lib/docker"
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

扩容时，请不要在inventory文件master组中保留旧服务器信息。

```
ansible-playbook k8s.yml -i inventory -t init -l master
ansible-playbook k8s.yml -i inventory -t cert,install_master 
```

#### 4.4、扩容node节点

扩容时，请不要在inventory文件node组中保留旧服务器信息。

```
ansible-playbook k8s.yml -i inventory -t init -l node
ansible-playbook k8s.yml -i inventory -t cert,install_node
```

#### 4.5、替换集群证书

先备份并删除证书目录，然后执行以下步骤

```
ansible-playbook k8s.yml -i inventory -t cert
ansible-playbook k8s.yml -i inventory -t dis_certs
```

然后依次重启每个节点。


