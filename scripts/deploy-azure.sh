#!/bin/bash
# QAMill Azure Deployment Automation Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
RESOURCE_GROUP=${RESOURCE_GROUP:-"qamill-prod"}
LOCATION=${LOCATION:-"eastus"}
CLUSTER_NAME=${CLUSTER_NAME:-"qamill-aks"}
REGISTRY_NAME=${REGISTRY_NAME:-"qamillregistry"}
DB_SERVER=${DB_SERVER:-"qamill-postgres"}
REDIS_NAME=${REDIS_NAME:-"qamill-redis"}
STORAGE_ACCOUNT=${STORAGE_ACCOUNT:-"qamill$(date +%s)"}
VAULT_NAME=${VAULT_NAME:-"qamill-vault"}

echo -e "${YELLOW}QAMill Azure Deployment Script${NC}"
echo "========================================"
echo "Resource Group: $RESOURCE_GROUP"
echo "Location: $LOCATION"
echo "Cluster: $CLUSTER_NAME"
echo ""

# Function to check if Azure CLI is installed
check_azure_cli() {
    if ! command -v az &> /dev/null; then
        echo -e "${RED}Azure CLI is not installed. Installing...${NC}"
        curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
    else
        echo -e "${GREEN}✓ Azure CLI found${NC}"
    fi
}

# Function to check if kubectl is installed
check_kubectl() {
    if ! command -v kubectl &> /dev/null; then
        echo -e "${RED}kubectl is not installed. Installing...${NC}"
        curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
        sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
    else
        echo -e "${GREEN}✓ kubectl found${NC}"
    fi
}

# Function to login to Azure
login_azure() {
    echo -e "${YELLOW}Logging in to Azure...${NC}"
    az login
}

# Function to create resource group
create_resource_group() {
    echo -e "${YELLOW}Creating resource group: $RESOURCE_GROUP${NC}"

    if az group exists --name $RESOURCE_GROUP --query True -o json > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Resource group already exists${NC}"
    else
        az group create \
            --name $RESOURCE_GROUP \
            --location $LOCATION
        echo -e "${GREEN}✓ Resource group created${NC}"
    fi
}

# Function to create container registry
create_container_registry() {
    echo -e "${YELLOW}Creating container registry: $REGISTRY_NAME${NC}"

    az acr create \
        --resource-group $RESOURCE_GROUP \
        --name $REGISTRY_NAME \
        --sku Standard \
        --admin-enabled true

    echo -e "${GREEN}✓ Container registry created${NC}"
}

# Function to build and push Docker image
build_and_push_image() {
    echo -e "${YELLOW}Building and pushing Docker image...${NC}"

    az acr login --name $REGISTRY_NAME

    az acr build \
        --registry $REGISTRY_NAME \
        --image qamill:1.2.0 \
        --file Dockerfile .

    echo -e "${GREEN}✓ Docker image built and pushed${NC}"
}

# Function to create AKS cluster
create_aks_cluster() {
    echo -e "${YELLOW}Creating AKS cluster: $CLUSTER_NAME${NC}"

    if az aks show --resource-group $RESOURCE_GROUP --name $CLUSTER_NAME > /dev/null 2>&1; then
        echo -e "${GREEN}✓ AKS cluster already exists${NC}"
    else
        az aks create \
            --resource-group $RESOURCE_GROUP \
            --name $CLUSTER_NAME \
            --node-count 3 \
            --vm-set-type VirtualMachineScaleSets \
            --load-balancer-sku standard \
            --enable-managed-identity \
            --network-plugin azure \
            --network-policy azure \
            --docker-bridge-address 172.17.0.1/16 \
            --service-cidr 10.0.0.0/16 \
            --dns-service-ip 10.0.0.10 \
            --attach-acr $REGISTRY_NAME \
            --generate-ssh-keys

        echo -e "${GREEN}✓ AKS cluster created${NC}"
    fi

    # Get credentials
    az aks get-credentials \
        --resource-group $RESOURCE_GROUP \
        --name $CLUSTER_NAME
}

# Function to create PostgreSQL database
create_postgresql() {
    echo -e "${YELLOW}Creating Azure Database for PostgreSQL: $DB_SERVER${NC}"

    if az postgres server show --resource-group $RESOURCE_GROUP --name $DB_SERVER > /dev/null 2>&1; then
        echo -e "${GREEN}✓ PostgreSQL server already exists${NC}"
    else
        DB_PASSWORD=$(openssl rand -base64 16)

        az postgres server create \
            --resource-group $RESOURCE_GROUP \
            --name $DB_SERVER \
            --location $LOCATION \
            --admin-user qamill_admin \
            --admin-password "$DB_PASSWORD" \
            --sku-name B_Gen5_1 \
            --storage-size 51200 \
            --version 13

        echo -e "${GREEN}✓ PostgreSQL server created${NC}"
        echo "Database Password: $DB_PASSWORD (save this!)"

        # Create database
        az postgres db create \
            --resource-group $RESOURCE_GROUP \
            --server-name $DB_SERVER \
            --name qamill

        echo -e "${GREEN}✓ Database created${NC}"
    fi
}

# Function to create Redis cache
create_redis() {
    echo -e "${YELLOW}Creating Azure Cache for Redis: $REDIS_NAME${NC}"

    if az redis show --resource-group $RESOURCE_GROUP --name $REDIS_NAME > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Redis cache already exists${NC}"
    else
        az redis create \
            --resource-group $RESOURCE_GROUP \
            --name $REDIS_NAME \
            --location $LOCATION \
            --sku Basic \
            --vm-size c0

        echo -e "${GREEN}✓ Redis cache created${NC}"
    fi
}

# Function to create storage account
create_storage() {
    echo -e "${YELLOW}Creating Azure Storage Account: $STORAGE_ACCOUNT${NC}"

    az storage account create \
        --resource-group $RESOURCE_GROUP \
        --name $STORAGE_ACCOUNT \
        --location $LOCATION \
        --sku Standard_LRS

    # Create blob container
    az storage container create \
        --account-name $STORAGE_ACCOUNT \
        --name qamill-storage

    echo -e "${GREEN}✓ Storage account created${NC}"
}

# Function to create Key Vault
create_keyvault() {
    echo -e "${YELLOW}Creating Azure Key Vault: $VAULT_NAME${NC}"

    if az keyvault show --resource-group $RESOURCE_GROUP --name $VAULT_NAME > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Key Vault already exists${NC}"
    else
        az keyvault create \
            --resource-group $RESOURCE_GROUP \
            --name $VAULT_NAME \
            --location $LOCATION

        echo -e "${GREEN}✓ Key Vault created${NC}"
    fi
}

# Function to create Kubernetes secrets
create_k8s_secrets() {
    echo -e "${YELLOW}Creating Kubernetes secrets...${NC}"

    # Create namespace
    kubectl create namespace qamill --dry-run=client -o yaml | kubectl apply -f -

    # Get database URL
    DB_HOST=$(az postgres server show \
        --resource-group $RESOURCE_GROUP \
        --name $DB_SERVER \
        --query "fullyQualifiedDomainName" \
        --output tsv)

    # Get Redis credentials
    REDIS_KEY=$(az redis list-keys \
        --resource-group $RESOURCE_GROUP \
        --name $REDIS_NAME \
        --query "primaryKey" \
        --output tsv)
    REDIS_HOST=$(az redis show \
        --resource-group $RESOURCE_GROUP \
        --name $REDIS_NAME \
        --query "hostName" \
        --output tsv)

    # Create secret
    kubectl create secret generic qamill-secrets \
        --from-literal=DATABASE_URL="postgresql://qamill_admin:CHANGE_PASSWORD@$DB_HOST:5432/qamill" \
        --from-literal=REDIS_URL="redis://:$REDIS_KEY@$REDIS_HOST:6379" \
        --from-literal=AUTH_JWT_SECRET="$(openssl rand -base64 32)" \
        --from-literal=OAUTH_GITHUB_CLIENT_ID="YOUR_GITHUB_ID" \
        --from-literal=OAUTH_GITHUB_CLIENT_SECRET="YOUR_GITHUB_SECRET" \
        --from-literal=OAUTH_GOOGLE_CLIENT_ID="YOUR_GOOGLE_ID" \
        --from-literal=OAUTH_GOOGLE_CLIENT_SECRET="YOUR_GOOGLE_SECRET" \
        -n qamill \
        --dry-run=client -o yaml | kubectl apply -f -

    echo -e "${GREEN}✓ Kubernetes secrets created${NC}"
}

# Function to deploy to AKS
deploy_to_aks() {
    echo -e "${YELLOW}Deploying to AKS...${NC}"

    # Update image URL in manifest
    sed -i "s|qamill:1.2.0|$REGISTRY_NAME.azurecr.io/qamill:1.2.0|g" k8s-deployment.yaml

    # Apply manifests
    kubectl apply -f k8s-deployment.yaml

    # Wait for rollout
    kubectl rollout status deployment/qamill-api -n qamill --timeout=10m

    echo -e "${GREEN}✓ Deployment complete${NC}"
}

# Function to get service details
get_service_details() {
    echo -e "${YELLOW}Service Details:${NC}"
    echo ""

    kubectl get services -n qamill
    echo ""

    # Get load balancer IP if available
    EXTERNAL_IP=$(kubectl get service qamill-api -n qamill \
        --template="{{range .status.loadBalancer.ingress}}{{.ip}}{{end}}" 2>/dev/null || echo "pending")

    if [ "$EXTERNAL_IP" != "pending" ]; then
        echo -e "${GREEN}External IP: $EXTERNAL_IP${NC}"
    fi
}

# Main execution
main() {
    echo ""

    # Check prerequisites
    check_azure_cli
    check_kubectl

    # Ask for confirmation
    read -p "Continue with deployment? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}Deployment cancelled${NC}"
        exit 1
    fi

    # Run deployment steps
    login_azure
    create_resource_group
    create_container_registry
    build_and_push_image
    create_aks_cluster
    create_postgresql
    create_redis
    create_storage
    create_keyvault
    create_k8s_secrets
    deploy_to_aks
    get_service_details

    echo ""
    echo -e "${GREEN}================================${NC}"
    echo -e "${GREEN}Deployment completed successfully!${NC}"
    echo -e "${GREEN}================================${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Configure your domain DNS to point to the service IP"
    echo "2. Set up SSL certificates"
    echo "3. Update OAuth credentials in Key Vault"
    echo "4. Configure monitoring and logging"
}

# Run main function
main "$@"
