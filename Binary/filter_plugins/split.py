
#   {{ hostname | split_hostname }}
# 

def split_hostname(hostname):
    return "".join(hostname.split("-")[-2:])

class FilterModule(object):
    def filters(self):
        return {'split_hostname': split_hostname}