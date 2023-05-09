import os
import requests

# 定义要下载的 GitHub 仓库
links = [
    "https://github.com/containernetworking/plugins/releases/download/v1.2.0/cni-plugins-linux-amd64-v1.2.0.tgz",
    "https://github.com/kubernetes-sigs/cri-tools/releases/download/v1.27.0/crictl-v1.27.0-linux-amd64.tar.gz",
    "https://github.com/opencontainers/runc/releases/download/v1.1.7/runc.amd64",
    "https://github.com/containerd/containerd/releases/download/v1.6.21/containerd-1.6.21-linux-amd64.tar.gz",
    "https://github.com/etcd-io/etcd/releases/download/v3.5.8/etcd-v3.5.8-linux-amd64.tar.gz",
    "https://storage.googleapis.com/kubernetes-release/release/v1.27.1/bin/linux/amd64/kube-apiserver",
    "https://storage.googleapis.com/kubernetes-release/release/v1.27.1/bin/linux/amd64/kube-controller-manager",
    "https://storage.googleapis.com/kubernetes-release/release/v1.27.1/bin/linux/amd64/kube-scheduler",
    "https://storage.googleapis.com/kubernetes-release/release/v1.27.1/bin/linux/amd64/kubelet",
    "https://storage.googleapis.com/kubernetes-release/release/v1.27.1/bin/linux/amd64/kube-proxy",
    "https://storage.googleapis.com/kubernetes-release/release/v1.27.1/bin/linux/amd64/kubectl"
]

path = "mirrors"

# 循环下载每个文件
for link in links:
    # 发送 GET 请求，获取响应
    response = requests.get(link)

    # 定义路径
    file_path = link.split('.com/')[1]
    file_name = file_path.split('/')[-1]
    down_path = file_path.split(file_name)[0]
    full_path = os.path.join(path, down_path)

    # 判断目录是否存在，不存在则创建
    if not os.path.exists(full_path):
       os.makedirs(full_path)

    # 如果响应状态码为 200，则表示请求成功
    if response.status_code == 200:
        # 构造响应体的 URL，以便将其下载
        response_url = f"{link}?download=true"

        # 发送 GET 请求，获取响应体
        response_body = requests.get(response_url)

        # 如果响应状态码为 200，则表示请求成功
        if response_body.status_code == 200:
            # 将响应体保存到本地文件
            with open(os.path.join(full_path, file_name), "wb") as f:
                f.write(response_body.content)
                print(f"成功下载{file_name}文件!")
        else:
            print(f"无法下载{file_name}文件，响应状态码为{response_body.status_code}")
    else:
        print(f"无法下载{file_name}文件，响应状态码为{response.status_code}")