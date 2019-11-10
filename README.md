本工具使用ansible playbook初始化系统配置、安装kubernetes高可用集群，并可进行节点扩容、替换集群证书等。本playbook安装kubernetes集群为静态Pod方式部署。



## 使用方法：

### 一、准备资源

请按照inventory格式修改对应资源

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

#本组机器不会进行系统初始化等操作，仅用做安装kubectl命令行
[kubectl]
172.16.90.204 hostname=master-01

[haproxy]
172.16.90.198 hostname=haproxy-01 type=MASTER priority=100
172.16.90.199 hostname=haproxy-02 type=BACKUP priority=90
[all:vars]
vip=172.16.90.200

#本组内填写node服务器及主机名
[node]
172.16.90.207 hostname=node-01
172.16.90.208 hostname=node-02
172.16.90.209 hostname=node-03
```



###  二、修改相关配置

编辑group_vars/all.yml文件，填入自己的配置

| 配置项             | 说明                                                         |
| ------------------ | ------------------------------------------------------------ |
| ssl_dir            | 签发ssl证书保存路径，ansible控制端机器上的路径。默认签发10年有效期的证书 |
| kubernetes_version | kubernetes 版本                                              |
| docker_version     | 可通过查看版本yum list docker-ce --showduplicates            |
| service_ip_range   | 指定k8s集群service的网段                                     |
| pod_ip_range       | 指定k8s集群pod的网段                                         |

- 请将etcd安装在独立的服务器上，不建议跟master安装在一起




### 三、使用方法

#### 3.1、安装ansible

在控制端机器执行以下命令安装ansible

```
yum -y install ansible
pip install netaddr
```

#### 3.2、部署集群

```
ansible-playbook k8s.yml -i inventory
```

如是公有云环境，则执行：

```
ansible-playbook k8s.yml -i inventory --skip-tags=install_haproxy,install_keepalived
```

⚠️：默认使用calico ipip网络，部署成功后，可以自行修改。

#### 3.3、扩容mater节点

```
ansible-playbook k8s.yml -i inventory -t init -l master
ansible-playbook k8s.yml -i inventory -t cert,install_master 
```

#### 3.4、扩容node节点

```
ansible-playbook k8s.yml -i inventory -t init -l node
ansible-playbook k8s.yml -i inventory -t cert,install_node
```

#### 3.5、替换集群证书

先备份并删除证书目录，然后执行以下步骤

```
ansible-playbook k8s.yml -i inventory -t cert
ansible-playbook k8s.yml -i inventory -t dis_certs
```

然后依次重启每个节点。



### kubernetes HA架构

![k8s](kubernetes.png)


