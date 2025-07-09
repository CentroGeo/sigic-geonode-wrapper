#!/bin/bash
set -e

# This script is used to fix network issues by restarting the network service.

sh set-netplan-mtu-safe.sh
sh set-docker-mtu-safe.sh
sh create-sigic-network.sh