import ipaddress
import time

def is_ip_in_subnet(ip_str, subnet):
    try:
        ip = ipaddress.ip_address(ip_str)
        return ip in subnet
    except (ValueError, ipaddress.AddressValueError):
        return False
    
startTime = time.time_ns()

subnet_str = '2001:4860:4801:34::/64'
if '/' in subnet_str:
    subnet = ipaddress.ip_network(subnet_str, strict=False)
else:
    subnet = ipaddress.ip_network(f"{subnet_str}/{'128' if ip.version == 6 else '32'}", strict=False)

ip = ipaddress.ip_address('2001:4860:4801:34::a')
for _ in range(5000):
    print(is_ip_in_subnet(ip, subnet))
print('Time elapsed: ', (time.time_ns() - startTime)/1000000, 'ms')