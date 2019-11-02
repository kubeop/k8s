本工具使用ansible playbook初始化系统配置、安装kubernetes高可用集群，并可进行节点扩容、替换集群证书等。



## 使用方法：

### 一、准备资源

请按照inventory格式修改对应资源

```
#本组内填写etcd服务器及主机名
[etcd]
172.17.15.233 hostname=etcd-01
172.17.15.234 hostname=etcd-02
172.17.15.235 hostname=etcd-03

#本组内填写master服务器及主机名
[master]
172.17.15.238 hostname=master-01
172.17.15.239 hostname=master-02
172.17.15.240 hostname=master-03


#本组机器不会进行系统初始化等操作，仅用做安装kubectl命令行
[kubectl]
172.17.15.238 hostname=master-01

#本组机器不会进行系统初始化等操作，只是apiserver证书签发时使用
[k8s_service]
10.64.0.1        #shoule be k8s servcie first ip
172.17.15.200    #shoule be k8s apiserver slb ip
#本组域名不会进行系统初始化等操作，只是apiserver证书签发时使用，不需要进行修改
[k8s_domain]
kubernetes
kubernetes.default
kubernetes.default.svc
kubernetes.default.svc.cluster
kubernetes.default.svc.cluster.local

[haproxy]
172.17.15.247 hostname=haproxy-01 type=MASTER priority=100
172.17.15.248 hostname=haproxy-02 type=BACKUP priority=90
[haproxy:vars]
vip=172.17.15.200

#本组内填写node服务器及主机名
[node]
172.17.15.243 hostname=node-01
172.17.15.244 hostname=node-02
172.17.15.245 hostname=node-03
```



###  二、修改相关配置

编辑group_vars/all.yml文件，填入自己的配置

| 配置项           | 说明                                                         |
| ---------------- | ------------------------------------------------------------ |
| disk             | 指定机器数据盘盘符。本脚本会自动格式化并挂载磁盘             |
| download_url     | k8s二进制文件下载地址，默认是官方下载地址，可能会比较慢或者下载失败，可自己先行下载配置文件服务器. |
| docker_version   | 可通过查看版本yum list docker-ce.x86_64 --showduplicates     |
| ssl_dir          | 签发ssl证书保存路径，ansible控制端机器上的路径。默认签发10年有效期的证书 |
| service_ip_range | 指定k8s集群service的网段                                     |
| pod_ip_range     | 指定k8s集群pod的网段                                         |

- 注：以下程序默认数据目录

- 请将etcd安装在独立的服务器上，不建议跟master安装在一起

- etcd数据目录: /var/lib/etcd

  docker数据目录: /var/lib/docker

  kubelet数据目录: /var/lib/kubelet

- 下载路径：

  ```
  ${download_url}/kubectl
  ```

  注：自行去https://github.com/kubernetes/kubernetes下载对应版本，将二进制文件解压至下载服务器对应目录

### 三、使用方法

#### 3.1、安装ansible

在控制端机器执行以下命令安装ansible

```
yum -y install ansible
```

#### 3.2、部署集群

```
ansible-playbook k8s.yml -i inventory
```

如是公有云环境，则执行：

```
ansible-playbook k8s.yml -i inventory --skip-tags=install_haproxy,install_keepalived
```

⚠️：默认使用calico网络插件，可自行下载flannel yaml安装flannel网络插件

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

#### 3.3、替换集群证书

先删除ca、apiserver证书，然后执行以下步骤

```
ansible-playbook k8s.yml -i inventory -t cert
ansible-playbook k8s.yml -i inventory -t dis_certs,restart_master,restart_node,restart_etcd
```



### kubernetes HA架构

![k8s](kubernetes.png)


