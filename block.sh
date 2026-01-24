while read ip; do
    if [[ $ip =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        sudo iptables -A INPUT -s $ip -j DROP
        echo "Blocked IP: $ip"
    fi
done < /tmp/ips_to_block.txt
