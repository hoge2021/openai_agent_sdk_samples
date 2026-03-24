# まずVPC IDを変数に格納（タグNameで特定する場合）
VPC_ID=$(aws ec2 describe-vpcs \
  --filters "Name=tag:Name,Values=対象のVPC名をここに入れる" \
  --query 'Vpcs[0].VpcId' --output text)
echo "VPC_ID: ${VPC_ID}"

# VPC詳細
aws ec2 describe-vpcs --vpc-ids "${VPC_ID}" \
  --query 'Vpcs[].{VpcId:VpcId,CidrBlock:CidrBlock,Tags:Tags}' --output json

# サブネット（6つ）
aws ec2 describe-subnets --filters "Name=vpc-id,Values=${VPC_ID}" \
  --query 'Subnets[].{SubnetId:SubnetId,CidrBlock:CidrBlock,AZ:AvailabilityZone,Tags:Tags}' --output json

# ルートテーブル（8つ）
aws ec2 describe-route-tables --filters "Name=vpc-id,Values=${VPC_ID}" \
  --query 'RouteTables[].{RouteTableId:RouteTableId,Associations:Associations[].SubnetId,Tags:Tags}' --output json

# NAT Gateway（2つ）― EIP情報も含めて取得
aws ec2 describe-nat-gateways --filter "Name=vpc-id,Values=${VPC_ID}" \
  --query 'NatGateways[].{NatGatewayId:NatGatewayId,SubnetId:SubnetId,PublicIp:NatGatewayAddresses[0].PublicIp,AllocationId:NatGatewayAddresses[0].AllocationId,PrivateIp:NatGatewayAddresses[0].PrivateIp,Tags:Tags}' --output json

# NAT Gatewayに紐づくEIPの詳細
NAT_EIP_ALLOC_IDS=$(aws ec2 describe-nat-gateways --filter "Name=vpc-id,Values=${VPC_ID}" \
  --query 'NatGateways[].NatGatewayAddresses[].AllocationId' --output text)
if [ -n "${NAT_EIP_ALLOC_IDS}" ]; then
  aws ec2 describe-addresses --allocation-ids ${NAT_EIP_ALLOC_IDS} \
    --query 'Addresses[].{AllocationId:AllocationId,PublicIp:PublicIp,AssociationId:AssociationId,Tags:Tags}' --output json
fi

# Internet Gateway（1つ）
aws ec2 describe-internet-gateways --filters "Name=attachment.vpc-id,Values=${VPC_ID}" \
  --query 'InternetGateways[].{InternetGatewayId:InternetGatewayId,Tags:Tags}' --output json
