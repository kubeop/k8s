![](https://img.shields.io/github/forks/kubeop/k8s?style=social)
![](https://img.shields.io/github/watchers/kubeop/k8s?style=social )
![](https://img.shields.io/github/stars/kubeop/k8s?color=green&style=social)

## 支持的发行版

- AlmaLinux 8，9

- RockyLinux 8，9

- TencentOS 3.1

- Ubuntu Server 20.04，22.04，24.04

- Debian 12



## 支持平台

- amd64
- arm64



## 支持组件

- Core
  - [kubernetes](https://github.com/kubernetes/kubernetes)
  - [etcd](https://github.com/etcd-io/etcd)
  - [containerd](https://github.com/containerd/containerd)
- Network Plugin
  - [cni-plugins](https://github.com/containernetworking/plugins)
  - [calico](https://github.com/projectcalico/calico)
  - [cilium](https://github.com/cilium/cilium)
  - [flanneld](https://github.com/flannel-io/flannel)
  - [kube-router](https://github.com/cloudnativelabs/kube-router)
- Application
  - [coredns](https://github.com/coredns/coredns)
  - [node-local-dns](https://github.com/kubernetes/kubernetes/tree/master/cluster/addons/dns/nodelocaldns)
  - [metrics-server](https://github.com/kubernetes-sigs/metrics-server)
  - [nvidia_device_plugin](https://github.com/NVIDIA/k8s-device-plugin)
  - [helm](https://github.com/helm/helm)



## 开始配置

> 本脚本向前兼容，拉取最新代码，根据需求调整`group_vars/all.yml`和`inventory`中相关参数即可。
>
> 如需更新本地代码至最新，建议备份`group_vars/all.yml`和`inventory`并更新代码至最新，然后将原`group_vars/all.yml`和`inventory`中需要的配置添加到最新的`group_vars/all.yml`和`inventory`文件即可。



### 配置Ansible控制端

建议根据下表安装合适的Python版本和Ansible版本

| 组件                    | 版本     |
| ----------------------- | -------- |
| **Control Node Python** | >=3.9    |
| **Target Python**       | >=3.6    |
| **Ansible**             | >=2.14.0 |



安装Ansible

```shell
pip3 install "ansible>=7.0.0,<10.0.0" -i https://mirrors.ustc.edu.cn/pypi/web/simple
pip3 install "netaddr>=0.10.1" -i https://mirrors.ustc.edu.cn/pypi/web/simple
```

- 不同Python版本Anisble支持矩阵详情，请参考：https://docs.ansible.com/ansible-core/devel/reference_appendices/release_and_maintenance.html#ansible-core-support-matrix



### 开启双栈网络

在`group_vars/all.yml`配置中将ipv4_stack和ipv6_stack设置为`true`表明开启IPv4和IPv6双栈网络，将ipv4_stack设置为`true`表明开启IPv4单栈网络，将ipv6_stack设置为`true`表明开启IPv6单栈网络。使用IPv6网络之前请务必确认集群节点所在网络已开启支持IPv6。

⚠️：在云平台使用Calico IPIP时，请勿开启双栈网络，Calico IPv6网络不支持IPIP，[参考](https://github.com/projectcalico/calico/issues/5206)。



### 修改 inventory

请按照inventory模板格式修改对应资源

- 当haproxy和kube-apiserver部署在同一台服务器时，请确保端口不冲突。



### 配置 group_vars

编辑 group_vars/all.yml 文件，根据自己的实际环境进行配置。

请注意：

- **Kubernetes** 的最低版本要求为 v1.26

- 请尽量将etcd安装在独立的服务器上，不建议跟master安装在一起。数据盘尽量使用SSD盘。
- Pod 和Service IP网段建议使用保留私有IP段，建议（Pod IP不与Service IP重复，也不要与主机IP段重复，同时也避免与docker0网卡的网段冲突）从以下网段及子网选择：
  - Pod 网段
    - A类地址：10.0.0.0/8
    - B类地址：172.16.0.0/12
    - C类地址：192.168.0.0/16
  - Service网段
    - A类地址：10.0.0.0/16-24
    - B类地址：172.16-31.0.0/16-24
    - C类地址：192.168.0.0/16-24




### 挂载数据盘

如已经自行格式化并挂载目录，可以跳过此步骤。

```shell
ansible-playbook fdisk.yml -i inventory -e "disk=sdb dir=/data"
```

- 可选变量`-e "disk=sdb dir=/data num=1"`

如果是NVME的磁盘，请使用以下方式:

```shell
ansible-playbook fdisk.yml -i inventory -e "disk=nvme0n1 dir=/data num=p1"
```

⚠️：

- 此脚本会格式化{{disk}}指定的硬盘，并挂载到{{dir}}目录。
- 同时会将`/var/lib/etcd`、`/var/lib/containerd`、`/var/lib/kubelet`、`/var/log/pods`数据目录绑定到此数据盘`{{dir}}/containers/etcd`、`{{dir}}/containers/containerd`、`{{dir}}/containers/kubelet`、`{{dir}}/containers/pods`目录，以达到多个数据目录共用一个数据盘，而无需修改kubernetes相关数据目录。



如需不同目录挂载不同数据盘，可以使用以下命令单独挂载

```shell
ansible-playbook fdisk.yml -i inventory -l etcd -e "disk=sdb dir=/var/lib/etcd" --skip-tags=bind_dir
```

如已经格式化并挂载过数据盘，可以使用以下命令将数据目录绑定到数据盘

```shell
ansible-playbook fdisk.yml -i inventory -l master,worker -e "disk=sdb dir=/data" -t bind_dir
```



### 安装GPU驱动

当集群节点为GPU节点时，请先参考[nvidia](nvidia.md)完成驱动安装。



### 下载离线包

```shell
# 如从自建文件服务器下载，请修改 group_vars/all.yml 文件中的默认下载地址
ansible-playbook download.yml
```

- 请确保Ansible控制端可以访问**Internet**，否则无法下载离线安装包。
- 或在其他**Internet**节点下载后，按照对应目录结构拷贝到{{ download.dest }}目录中也可。



### 同步镜像

```shell
# 建议将 group_vars/all.yml 中定义的镜像自行同步至私有镜像仓库中，并将地址修改为私有镜像仓库地址
# 目前会自动将 group_vars/all.yml 中定义的镜像同步到阿里云镜像仓库，可能不稳定或失效。
```



## 部署集群

```shell
# 执行之前，请确认已经进行过磁盘分区
# 执行之前，请确认已经执行 ansible-playbook download.yml 完成安装包下载
ansible-playbook cluster.yml -i inventory
```

如是公有云/私有云环境，使用公有云/私有云的负载均衡即可（需提前配置好负载均衡），无需安装haproxy和keepalived。

```shell
ansible-playbook cluster.yml -i inventory --skip-tags=haproxy,keepalived
```

- 默认会对节点进行初始化操作，集群节点会取主机名最后两段和IP作为集群节点名称。

如果想让master节点也进行调度，可以使用以下参数

```shell
ansible-playbook cluster.yml -i inventory --skip-tags=create_master_taint
```



## 扩容节点

### 扩容master节点

扩容时，在inventory文件master组中依次添加新增服务器信息（执行时请务必使用-l参数指定IP）。

格式化挂载数据盘

```shell
ansible-playbook fdisk.yml -i inventory -l ${SCALE_MASTER_IP} -e "disk=sdb dir=/data"
```

执行生成节点证书

```shell
ansible-playbook cluster.yml -i inventory -t cert
```

执行节点初始化

```shell
ansible-playbook cluster.yml -i inventory -l ${SCALE_MASTER_IP} -t verify,init
```

执行节点扩容

```shell
ansible-playbook cluster.yml -i inventory -l ${SCALE_MASTER_IP} -t master,containerd,worker --skip-tags=bootstrap,create_worker_label
```



### 扩容worker节点

扩容时，在inventory文件worker组中依次添加新增服务器信息（执行时请务必使用-l参数指定IP）。

格式化挂载数据盘

```shell
ansible-playbook fdisk.yml -i inventory -l ${SCALE_WORKER_IP} -e "disk=sdb dir=/data"
```

执行生成节点证书

```shell
ansible-playbook cluster.yml -i inventory -t cert
```

执行节点初始化

```shell
ansible-playbook cluster.yml -i inventory -l ${SCALE_WORKER_IP} -t verify,init
```

执行节点扩容

```shell
ansible-playbook cluster.yml -i inventory -l ${SCALE_WORKER_IP} -t containerd,worker --skip-tags=bootstrap,create_master_label
```



## 替换集群证书

先备份并删除证书目录{{cert.dir}}，重新创建{{cert.dir}}，并将token、sa.pub、sa.key文件拷贝至新创建的{{cert.dir}}（这三个文件务必保留，不能更改），然后执行以下步骤重新生成证书并分发证书。

```shell
ansible-playbook cluster.yml -i inventory -t cert,dis_certs
```

然后依次重启每个节点。

重启etcd

```shell
ansible -i inventory etcd -m systemd -a "name=etcd state=restarted"
```

验证etcd

```shell
etcdctl endpoint health \
        --cacert=/etc/etcd/pki/etcd-ca.pem \
        --cert=/etc/etcd/pki/etcd-healthcheck-client.pem \
        --key=/etc/etcd/pki/etcd-healthcheck-client.key \
        --endpoints=https://10.43.75.201:2379,https://10.43.75.202:2379,https://10.43.75.203:2379
```

逐个删除旧的kubelet证书

```shell
ansible -i inventory master,worker -m shell -a "rm -rf /etc/kubernetes/pki/kubelet*"
```

- `-l`参数更换为具体节点IP。

逐个重启节点

```shell
ansible-playbook cluster.yml -i inventory -l ${IP} -t restart_apiserver,restart_controller,restart_scheduler,restart_kubelet,restart_proxy,healthcheck
```

- 如calico、metrics-server等服务也使用了集群证书，请记得一起更新相关证书。
- `-l`参数更换为具体节点IP。

重启网络插件

```shell
kubectl get pod -n kube-system | grep -v NAME | grep cilium | awk '{print $1}' | xargs kubectl -n kube-system delete pod
```

-  更新证书可能会导致网络插件异常，建议重启。
-  示例为重启cilium插件命令，请根据不同网络插件自行替换。



## 升级集群版本

请先编辑group_vars/all.yml，修改kubernetes.version为新版本。

下载新版本安装包

```shell
ansible-playbook download.yml
```

升级etcd（升级会自动重启etcd，可根据需求自行选择是否升级）

```shell
ansible-playbook cluster.yml -i inventory -l ${IP} -t install_etcd,dis_etcd_config
```

- `-l`参数更换为具体节点IP。

安装kubernetes组件

```shell
ansible-playbook cluster.yml -i inventory -l ${IP} -t install_kubectl,install_master,install_worker
```

- `-l`参数更换为具体节点IP。

更新配置文件

```shell
ansible-playbook cluster.yml -i inventory -l ${IP} -t dis_master_config,dis_worker_config
```

- `-l`参数更换为具体节点IP。
- 使用v7.x之前版本部署的集群，因v7.x之后调整节点名称，不建议执行

清空节点

```shell
kubectl drain --ignore-daemonsets --force <节点名称>
```

升级containerd组件（升级会自动重启containerd，可根据需求自行选择是否升级）

```shell
ansible-playbook cluster.yml -i inventory -l ${IP} -t install_runc,install_cni,install_containerd,install_critools,containerd_config
```

- `-l`参数更换为具体节点IP。

然后依次重启每个kubernetes组件。

```shell
ansible-playbook cluster.yml -i inventory -l ${IP} -t restart_apiserver,restart_controller,restart_scheduler,restart_kubelet,restart_proxy,healthcheck
```

- `-l`参数更换为具体节点IP。

恢复调度

```shell
kubectl uncordon <节点名称>
```



## 清理集群节点

```shell
ansible-playbook reset.yml -i inventory -l ${IP} -e "flush_iptables=true"
```

