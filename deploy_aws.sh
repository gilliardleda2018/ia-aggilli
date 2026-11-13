#!/bin/bash
# ============================================================
# ANI — Deploy completo na AWS
# Conta: 614471945241 | Região: sa-east-1
# ============================================================

set -e  # Para se der qualquer erro

# ── Variáveis ────────────────────────────────────────────────
ACCOUNT_ID="614471945241"
REGION="sa-east-1"
APP="ani"
ECR_REPO_COORDENADOR="ani-coordenador"
ECR_REPO_API="ani-api"
CLUSTER_NAME="ani-cluster"
VPC_CIDR="10.0.0.0/16"
SUBNET_CIDR_A="10.0.1.0/24"
SUBNET_CIDR_B="10.0.2.0/24"

echo ""
echo "🌱 ANI — Deploy na AWS"
echo "======================================"
echo "Conta:  $ACCOUNT_ID"
echo "Região: $REGION"
echo ""

# ── PASSO 1: ECR — Repositórios de imagens Docker ───────────
echo "📦 PASSO 1: Criando repositórios ECR..."

aws ecr create-repository \
  --repository-name $ECR_REPO_COORDENADOR \
  --region $REGION \
  --image-scanning-configuration scanOnPush=true \
  2>/dev/null && echo "  ✅ ECR $ECR_REPO_COORDENADOR criado" \
  || echo "  ⏭  ECR $ECR_REPO_COORDENADOR já existe"

aws ecr create-repository \
  --repository-name $ECR_REPO_API \
  --region $REGION \
  --image-scanning-configuration scanOnPush=true \
  2>/dev/null && echo "  ✅ ECR $ECR_REPO_API criado" \
  || echo "  ⏭  ECR $ECR_REPO_API já existe"

# ── PASSO 2: Build e push das imagens Docker ─────────────────
echo ""
echo "🐳 PASSO 2: Build e push das imagens..."

# Login no ECR
aws ecr get-login-password --region $REGION | \
  docker login --username AWS \
  --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

# Build coordenador
echo "  🔨 Build coordenador..."
docker build \
  -f /home/gilliard/ia-aggilli/docker/Dockerfile.coordenador \
  -t $ECR_REPO_COORDENADOR:latest \
  /home/gilliard/ia-aggilli/

# Tag e push coordenador
docker tag $ECR_REPO_COORDENADOR:latest \
  $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$ECR_REPO_COORDENADOR:latest
docker push \
  $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$ECR_REPO_COORDENADOR:latest
echo "  ✅ Coordenador enviado para ECR"

# Build API
echo "  🔨 Build API..."
docker build \
  -f /home/gilliard/ia-aggilli/docker/Dockerfile.coordenador \
  -t $ECR_REPO_API:latest \
  /home/gilliard/ia-aggilli/

# Tag e push API
docker tag $ECR_REPO_API:latest \
  $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$ECR_REPO_API:latest
docker push \
  $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$ECR_REPO_API:latest
echo "  ✅ API enviada para ECR"

# ── PASSO 3: VPC e Rede ──────────────────────────────────────
echo ""
echo "🌐 PASSO 3: Criando VPC e rede..."

# Cria VPC
VPC_ID=$(aws ec2 create-vpc \
  --cidr-block $VPC_CIDR \
  --region $REGION \
  --tag-specifications "ResourceType=vpc,Tags=[{Key=Name,Value=ani-vpc}]" \
  --query 'Vpc.VpcId' --output text)
echo "  ✅ VPC criada: $VPC_ID"

# Habilita DNS
aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-hostnames
aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-support

# Internet Gateway
IGW_ID=$(aws ec2 create-internet-gateway \
  --region $REGION \
  --tag-specifications "ResourceType=internet-gateway,Tags=[{Key=Name,Value=ani-igw}]" \
  --query 'InternetGateway.InternetGatewayId' --output text)
aws ec2 attach-internet-gateway --internet-gateway-id $IGW_ID --vpc-id $VPC_ID
echo "  ✅ Internet Gateway: $IGW_ID"

# Subnets
AZ_A="${REGION}a"
AZ_B="${REGION}b"

SUBNET_A=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block $SUBNET_CIDR_A \
  --availability-zone $AZ_A \
  --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=ani-subnet-a}]" \
  --query 'Subnet.SubnetId' --output text)

SUBNET_B=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block $SUBNET_CIDR_B \
  --availability-zone $AZ_B \
  --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=ani-subnet-b}]" \
  --query 'Subnet.SubnetId' --output text)

echo "  ✅ Subnets: $SUBNET_A | $SUBNET_B"

# Route Table
RTB_ID=$(aws ec2 create-route-table \
  --vpc-id $VPC_ID \
  --tag-specifications "ResourceType=route-table,Tags=[{Key=Name,Value=ani-rtb}]" \
  --query 'RouteTable.RouteTableId' --output text)
aws ec2 create-route --route-table-id $RTB_ID \
  --destination-cidr-block 0.0.0.0/0 --gateway-id $IGW_ID
aws ec2 associate-route-table --route-table-id $RTB_ID --subnet-id $SUBNET_A
aws ec2 associate-route-table --route-table-id $RTB_ID --subnet-id $SUBNET_B
echo "  ✅ Rotas configuradas"

# ── PASSO 4: Security Groups ─────────────────────────────────
echo ""
echo "🔒 PASSO 4: Criando Security Groups..."

SG_ID=$(aws ec2 create-security-group \
  --group-name ani-sg \
  --description "ANI Security Group" \
  --vpc-id $VPC_ID \
  --region $REGION \
  --tag-specifications "ResourceType=security-group,Tags=[{Key=Name,Value=ani-sg}]" \
  --query 'GroupId' --output text)

# Libera portas da ANI
aws ec2 authorize-security-group-ingress --group-id $SG_ID \
  --protocol tcp --port 8080 --cidr 0.0.0.0/0  # API REST
aws ec2 authorize-security-group-ingress --group-id $SG_ID \
  --protocol tcp --port 9090 --cidr 0.0.0.0/0  # gRPC nós
aws ec2 authorize-security-group-ingress --group-id $SG_ID \
  --protocol tcp --port 443  --cidr 0.0.0.0/0  # HTTPS
aws ec2 authorize-security-group-ingress --group-id $SG_ID \
  --protocol tcp --port 22   --cidr 0.0.0.0/0  # SSH

echo "  ✅ Security Group: $SG_ID"
echo "  ✅ Portas liberadas: 8080 (API), 9090 (gRPC), 443, 22"

# ── PASSO 5: ECS Cluster ─────────────────────────────────────
echo ""
echo "⚙️  PASSO 5: Criando ECS Cluster..."

aws ecs create-cluster \
  --cluster-name $CLUSTER_NAME \
  --region $REGION \
  --capacity-providers FARGATE FARGATE_SPOT \
  --default-capacity-provider-strategy \
    capacityProvider=FARGATE_SPOT,weight=4 \
    capacityProvider=FARGATE,weight=1 \
  --tags key=projeto,value=ani \
  2>/dev/null && echo "  ✅ Cluster $CLUSTER_NAME criado" \
  || echo "  ⏭  Cluster já existe"

# ── PASSO 6: IAM Role para ECS ───────────────────────────────
echo ""
echo "🔑 PASSO 6: Criando IAM Role para ECS..."

# Trust policy
cat > /tmp/ecs-trust-policy.json << 'TRUST'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "ecs-tasks.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
TRUST

aws iam create-role \
  --role-name ani-ecs-task-role \
  --assume-role-policy-document file:///tmp/ecs-trust-policy.json \
  2>/dev/null && echo "  ✅ Role ani-ecs-task-role criada" \
  || echo "  ⏭  Role já existe"

aws iam attach-role-policy \
  --role-name ani-ecs-task-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy \
  2>/dev/null || true

# ── PASSO 7: Task Definitions ────────────────────────────────
echo ""
echo "📋 PASSO 7: Registrando Task Definitions..."

# Task da API
cat > /tmp/ani-api-task.json << TASK
{
  "family": "ani-api",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::${ACCOUNT_ID}:role/ani-ecs-task-role",
  "containerDefinitions": [{
    "name": "ani-api",
    "image": "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPO_API}:latest",
    "portMappings": [
      {"containerPort": 8080, "protocol": "tcp"},
      {"containerPort": 8000, "protocol": "tcp"}
    ],
    "environment": [
      {"name": "ANI_VERSAO", "value": "1.0"},
      {"name": "LOG_LEVEL",  "value": "INFO"}
    ],
    "logConfiguration": {
      "logDriver": "awslogs",
      "options": {
        "awslogs-group": "/ecs/ani-api",
        "awslogs-region": "${REGION}",
        "awslogs-stream-prefix": "ani",
        "awslogs-create-group": "true"
      }
    },
    "essential": true
  }]
}
TASK

aws ecs register-task-definition \
  --cli-input-json file:///tmp/ani-api-task.json \
  --region $REGION > /dev/null
echo "  ✅ Task Definition ani-api registrada"

# Task do coordenador
cat > /tmp/ani-coordenador-task.json << TASK
{
  "family": "ani-coordenador",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::${ACCOUNT_ID}:role/ani-ecs-task-role",
  "containerDefinitions": [{
    "name": "ani-coordenador",
    "image": "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPO_COORDENADOR}:latest",
    "portMappings": [
      {"containerPort": 9090, "protocol": "tcp"},
      {"containerPort": 8000, "protocol": "tcp"}
    ],
    "environment": [
      {"name": "ANI_HOST",   "value": "0.0.0.0"},
      {"name": "ANI_PORT",   "value": "9090"},
      {"name": "ANI_ROUNDS", "value": "10000"},
      {"name": "LOG_LEVEL",  "value": "INFO"}
    ],
    "logConfiguration": {
      "logDriver": "awslogs",
      "options": {
        "awslogs-group": "/ecs/ani-coordenador",
        "awslogs-region": "${REGION}",
        "awslogs-stream-prefix": "ani",
        "awslogs-create-group": "true"
      }
    },
    "essential": true
  }]
}
TASK

aws ecs register-task-definition \
  --cli-input-json file:///tmp/ani-coordenador-task.json \
  --region $REGION > /dev/null
echo "  ✅ Task Definition ani-coordenador registrada"

# ── PASSO 8: ECS Services ────────────────────────────────────
echo ""
echo "🚀 PASSO 8: Subindo serviços ECS..."

# Serviço API
aws ecs create-service \
  --cluster $CLUSTER_NAME \
  --service-name ani-api \
  --task-definition ani-api \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={
    subnets=[$SUBNET_A,$SUBNET_B],
    securityGroups=[$SG_ID],
    assignPublicIp=ENABLED
  }" \
  --region $REGION > /dev/null \
  && echo "  ✅ Serviço ani-api subindo..." \
  || echo "  ⏭  Serviço ani-api já existe"

# Serviço Coordenador
aws ecs create-service \
  --cluster $CLUSTER_NAME \
  --service-name ani-coordenador \
  --task-definition ani-coordenador \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={
    subnets=[$SUBNET_A,$SUBNET_B],
    securityGroups=[$SG_ID],
    assignPublicIp=ENABLED
  }" \
  --region $REGION > /dev/null \
  && echo "  ✅ Serviço ani-coordenador subindo..." \
  || echo "  ⏭  Serviço ani-coordenador já existe"

# ── RESUMO FINAL ─────────────────────────────────────────────
echo ""
echo "======================================"
echo "✅ ANI DEPLOY CONCLUÍDO!"
echo "======================================"
echo ""
echo "📋 Recursos criados:"
echo "  VPC:              $VPC_ID"
echo "  Subnets:          $SUBNET_A | $SUBNET_B"
echo "  Security Group:   $SG_ID"
echo "  ECR Coordenador:  $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$ECR_REPO_COORDENADOR"
echo "  ECR API:          $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$ECR_REPO_API"
echo "  ECS Cluster:      $CLUSTER_NAME"
echo ""
echo "⏳ Aguardando tasks iniciarem (pode levar 2-3 min)..."
sleep 30

# Pega IP público da API
echo ""
echo "🔍 Buscando IP público da ANI..."
TASK_ARN=$(aws ecs list-tasks \
  --cluster $CLUSTER_NAME \
  --service-name ani-api \
  --region $REGION \
  --query 'taskArns[0]' --output text)

if [ "$TASK_ARN" != "None" ] && [ ! -z "$TASK_ARN" ]; then
  ENI_ID=$(aws ecs describe-tasks \
    --cluster $CLUSTER_NAME \
    --tasks $TASK_ARN \
    --region $REGION \
    --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' \
    --output text)

  PUBLIC_IP=$(aws ec2 describe-network-interfaces \
    --network-interface-ids $ENI_ID \
    --region $REGION \
    --query 'NetworkInterfaces[0].Association.PublicIp' \
    --output text)

  echo ""
  echo "🌍 ANI na nuvem!"
  echo "======================================"
  echo "  API:          http://$PUBLIC_IP:8080"
  echo "  Coordenador:  $PUBLIC_IP:9090"
  echo "  Métricas:     http://$PUBLIC_IP:8000"
  echo ""
  echo "🧪 Teste agora:"
  echo "  curl http://$PUBLIC_IP:8080/"
  echo ""
  echo "🌱 A ANI está viva na AWS!"
else
  echo ""
  echo "⏳ Tasks ainda iniciando. Verifique em 2 minutos:"
  echo "  aws ecs list-tasks --cluster $CLUSTER_NAME --region $REGION"
fi
