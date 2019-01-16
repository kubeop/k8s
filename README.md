### Kubernetes高可用集群

Kubernetes是容器集群管理系统，是一个开源的平台，可以实现容器集群的自动化部署、自动扩缩容、维护等功能。

通过Kubernetes你可以：

- 快速部署应用
- 快速扩展应用
- 无缝对接新的应用功能
- 节省资源，优化硬件资源的使用



本工具使用ansible playbook初始化系统配置、安装k8s高可用集群，并可进行节点扩容、替换集群证书等。

版本说明：

| 名称       | 版本       |
| ---------- | ---------- |
| kubernetes | 1.13.2     |
| docker     | 18.06.1    |
| system     | CentOS 7.6 |



##使用方法：

###一、准备资源

1.1、准备机器资源，机器需要使用一块数据盘用来存放数据

1.2、配置master负载均衡，公有云可以直接使用云负载均衡产品，自建机房等需配置haproxy等（后期支持自动配置haproxy）

1.3、请按照inventory格式将以上准备资源填写

```
#本组内填写etcd服务器及主机名
[etcd]
172.17.14.220    hostname=k8s-etcd-01

#本组内填写master服务器及主机名
[master]
172.17.14.223    hostname=k8s-master-01
172.17.14.224    hostname=k8s-master-02
172.17.14.225    hostname=k8s-master-03

#本组机器不会进行系统初始化等操作，仅用做安装kubectl命令行
[kubectl]
172.17.14.223    hostname=k8s-master-01

#本组机器不会进行系统初始化等操作，只是apiserver证书签发时使用
[k8s_service]
10.64.0.1        #service网段第一个IP
172.17.14.229    #apiserver 负载均衡IP

#本组内填写node服务器及主机名
[node]
172.17.14.226   hostname=k8s-node-01
172.17.14.227   hostname=k8s-node-02
172.17.14.228   hostname=k8s-node-03
172.17.14.231   hostname=k8s-node-04
```



### 二、修改相关配置

编辑group_vars/all文件，填入自己的参数

| 配置项                   | 说明                                                     |
| ------------------------ | -------------------------------------------------------- |
| disk                     | 指定机器数据盘盘符。本脚本会自动格式化并挂载磁盘         |
| data_dir                 | 指定机器数据盘挂在目录。本脚本会自动格式化并挂载磁盘     |
| zbx_server_ip            | 填写zabbix server的IP，系统初始化会自动安装zabbix-agent  |
| gpgkey                   | 选择使用vpc内网软件源还是外网软件源                      |
| download_url             | k8s二进制文件下载地址                                    |
| k8s_version              | 填写安装的k8s版本                                        |
| flannel_version          | 填写安装flannel版本                                      |
| docker_version           | 可通过查看版本yum list docker-ce.x86_64 --showduplicates |
| ssl_dir                  | 签发ssl证书保存路径，ansible控制端机器上的路径           |
| ssl_days                 | 签发ssl的有效期（单位：天）                              |
| apiserver_domain_name    | apiserver域名，签发证书和配置node节点连接master时会用到  |
| service_cluster_ip_range | 指定k8s集群service的网段                                 |
| pod_cluster_cidr         | 指定k8s集群pod的网段                                     |
| cluster_dns              | 指定集群dns服务IP                                        |
| harbor                   | 指定harbor镜像仓库地址                                   |

- 注：以下程序默认数据目录

- etcd数据目录: ${data_dir}/data/etcd

  docker数据目录: ${data_dir}/data/docker

  kubelet数据目录: ${data_dir}/data/kubelet

###三、使用方法

#### 3.1、安装ansible

在控制端机器执行以下命令安装ansible

```
pip install ansible
```

####3.2、部署集群

以下步骤都可单独执行，除系统初始化外，其他都可重复执行。也可单独指定tag执行部分模块

1、系统初始化

```
ansible-playbook k8s.yml -i inventory -t init
```

跳过zabbix agent部署

```
ansible-playbook k8s.yml -i inventory -t init --skip-tags=install_zabbix
```

2、签发证书

```
ansible-playbook k8s.yml -i inventory -t cert
```

3、安装etcd

```
ansible-playbook k8s.yml -i inventory -t install_etcd
```

4、安装master节点

```
ansible-playbook k8s.yml -i inventory -t install_master
```

5、安装node节点

```
ansible-playbook k8s.yml -i inventory -t install_node
```

6、全部安装

```
ansible-playbook k8s.yml -i inventory
```

7、扩容mater节点

```
ansible-playbook k8s.yml -i inventory -t init -l master
ansible-playbook k8s.yml -i inventory -t cert,install_master 
```

8、扩容node节点

```
ansible-playbook k8s.yml -i inventory -t init -l node
ansible-playbook k8s.yml -i inventory -t cert,install_node
```

####3.3、替换集群证书

先删除ca、apiserver证书，然后执行以下步骤

```
ansible-playbook k8s.yml -i inventory -t cert
ansible-playbook k8s.yml -i inventory -t dis_certs,restart_flannel,restart_master,restart_node,restart_etcd
```



### kubernetes HA架构

![k8s](kubernetes.png)