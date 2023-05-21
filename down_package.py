import os
import urllib.request
import traceback

def download_file(urls: list, path: str) -> tuple:
    successFiles = []
    failFiles = []
    for url in links:
        file_path = url.split('.com/')[1]
        fileName = file_path.split("/")[-1]
        filePath = os.path.join(path,  file_path.split(fileName)[0])
        if not os.path.exists(filePath):
            os.makedirs(filePath)
        try:
            print(f"Downloading {fileName} ......")
            urllib.request.urlretrieve(url, os.path.join(filePath, fileName))
            successFiles.append(fileName)
            print(
                f"Download {fileName} is over, file save to {os.path.join(filePath, fileName)}")
        except Exception as e:
            print(traceback.format_exc())
            failFiles.append(fileName)
            continue
    return (successFiles, failFiles)


if __name__ == "__main__":
    path = "./mirrors"
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
    successFiles, failFiles = download_file(links, path)
    print(f"下载结束, 下载成功文件：{successFiles}, 下载失败文件： {failFiles}")