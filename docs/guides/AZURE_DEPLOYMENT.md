# QAMill Azure Deployment Guide

**Complete guide for deploying QAMill to Microsoft Azure**

---

## Prerequisites

### Azure Account Setup
1. Create Azure account: https://azure.microsoft.com
2. Install Azure CLI:
   ```bash
   curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
   ```
3. Login to Azure:
   ```bash
   az login
   ```

### Required Azure Resources
- Azure Container Registry (ACR)
- Azure Kubernetes Service (AKS) - **Recommended for production**
- Azure Database for PostgreSQL
- Azure Cache for Redis
- Azure Storage Account
- Azure Application Insights

---

## Option 1: Kubernetes on Azure (AKS) - Recommended

### Step 1: Create Resource Group

```bash
# Set variables
RESOURCE_GROUP="qamill-prod"
LOCATION="eastus"
CLUSTER_NAME="qamill-aks"

# Create resource group
az group create \
  --name $RESOURCE_GROUP \
  --location $LOCATION
```

### Step 2: Create Azure Container Registry

```bash
REGISTRY_NAME="qamillregistry"

# Create ACR
az acr create \
  --resource-group $RESOURCE_GROUP \
  --name $REGISTRY_NAME \
  --sku Standard \
  --admin-enabled true

# Get login credentials
az acr credential show \
  --name $REGISTRY_NAME \
  --resource-group $RESOURCE_GROUP
```

### Step 3: Build and Push Docker Image

```bash
# Login to ACR
az acr login --name $REGISTRY_NAME

# Build image in ACR (faster than local)
az acr build \
  --registry $REGISTRY_NAME \
  --image qamill:1.2.0 \
  --file Dockerfile .

# Or build locally and push
docker build -t qamill:1.2.0 .
docker tag qamill:1.2.0 $REGISTRY_NAME.azurecr.io/qamill:1.2.0
docker push $REGISTRY_NAME.azurecr.io/qamill:1.2.0
```

### Step 4: Create AKS Cluster

```bash
# Create AKS cluster
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

# Get cluster credentials
az aks get-credentials \
  --resource-group $RESOURCE_GROUP \
  --name $CLUSTER_NAME
```

### Step 5: Create Azure Database for PostgreSQL

```bash
DB_SERVER="qamill-postgres"
DB_USER="qamill_admin"
DB_PASSWORD="ChangeMe@2024"  # Use strong password

# Create PostgreSQL server
az postgres server create \
  --resource-group $RESOURCE_GROUP \
  --name $DB_SERVER \
  --location $LOCATION \
  --admin-user $DB_USER \
  --admin-password $DB_PASSWORD \
  --sku-name B_Gen5_1 \
  --storage-size 51200 \
  --version 13

# Create database
az postgres db create \
  --resource-group $RESOURCE_GROUP \
  --server-name $DB_SERVER \
  --name qamill

# Get connection string
POSTGRES_URL=$(az postgres server show \
  --resource-group $RESOURCE_GROUP \
  --name $DB_SERVER \
  --query "fullyQualifiedDomainName" \
  --output tsv)
echo "PostgreSQL: postgresql://$DB_USER:$DB_PASSWORD@$POSTGRES_URL:5432/qamill"
```

### Step 6: Create Azure Cache for Redis

```bash
REDIS_NAME="qamill-redis"

# Create Redis cache
az redis create \
  --resource-group $RESOURCE_GROUP \
  --name $REDIS_NAME \
  --location $LOCATION \
  --sku Basic \
  --vm-size c0

# Get connection string
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
echo "Redis: redis://:$REDIS_KEY@$REDIS_HOST:6379"
```

### Step 7: Create Azure Storage Account

```bash
STORAGE_ACCOUNT="qamill$(date +%s)"

# Create storage account
az storage account create \
  --resource-group $RESOURCE_GROUP \
  --name $STORAGE_ACCOUNT \
  --location $LOCATION \
  --sku Standard_LRS

# Create blob container
az storage container create \
  --account-name $STORAGE_ACCOUNT \
  --name qamill-storage

# Get connection string
STORAGE_CONNECTION=$(az storage account show-connection-string \
  --resource-group $RESOURCE_GROUP \
  --name $STORAGE_ACCOUNT \
  --query "connectionString" \
  --output tsv)
```

### Step 8: Create Kubernetes Secrets

```bash
# Create namespace
kubectl create namespace qamill

# Create secrets
kubectl create secret generic qamill-secrets \
  --from-literal=DATABASE_URL="postgresql://$DB_USER:$DB_PASSWORD@$POSTGRES_URL:5432/qamill" \
  --from-literal=REDIS_URL="redis://:$REDIS_KEY@$REDIS_HOST:6379" \
  --from-literal=AUTH_JWT_SECRET="$(openssl rand -base64 32)" \
  --from-literal=OAUTH_GITHUB_CLIENT_ID="YOUR_GITHUB_ID" \
  --from-literal=OAUTH_GITHUB_CLIENT_SECRET="YOUR_GITHUB_SECRET" \
  --from-literal=OAUTH_GOOGLE_CLIENT_ID="YOUR_GOOGLE_ID" \
  --from-literal=OAUTH_GOOGLE_CLIENT_SECRET="YOUR_GOOGLE_SECRET" \
  -n qamill
```

### Step 9: Deploy to AKS

```bash
# Update k8s-deployment.yaml with your ACR registry URL
sed -i "s|qamill:1.2.0|$REGISTRY_NAME.azurecr.io/qamill:1.2.0|g" k8s-deployment.yaml

# Deploy
kubectl apply -f k8s-deployment.yaml

# Monitor deployment
kubectl rollout status deployment/qamill-api -n qamill

# Check pods
kubectl get pods -n qamill
```

### Step 10: Setup Azure Application Gateway (Optional Load Balancer)

```bash
# Create public IP
az network public-ip create \
  --resource-group $RESOURCE_GROUP \
  --name qamill-pip

# Get public IP
PUBLIC_IP=$(az network public-ip show \
  --resource-group $RESOURCE_GROUP \
  --name qamill-pip \
  --query "ipAddress" \
  --output tsv)
echo "Public IP: $PUBLIC_IP"
```

---

## Option 2: Container Instances (ACI) - Simple & Quick

For simpler deployments without full Kubernetes:

```bash
# Create container instance
az container create \
  --resource-group $RESOURCE_GROUP \
  --name qamill-api \
  --image $REGISTRY_NAME.azurecr.io/qamill:1.2.0 \
  --cpu 2 \
  --memory 4 \
  --environment-variables \
    DATABASE_URL="postgresql://..." \
    REDIS_URL="redis://..." \
    AUTH_JWT_SECRET="..." \
  --registry-login-server $REGISTRY_NAME.azurecr.io \
  --registry-username $REGISTRY_USER \
  --registry-password $REGISTRY_PASSWORD \
  --ports 8765 \
  --dns-name-label qamill-api \
  --protocol TCP

# Get public IP
az container show \
  --resource-group $RESOURCE_GROUP \
  --name qamill-api \
  --query "ipAddress.fqdn" \
  --output tsv
```

---

## Option 3: App Service (Easiest)

```bash
APP_SERVICE_PLAN="qamill-plan"
APP_SERVICE="qamill-app"

# Create App Service Plan
az appservice plan create \
  --name $APP_SERVICE_PLAN \
  --resource-group $RESOURCE_GROUP \
  --sku B1 \
  --is-linux

# Create App Service
az webapp create \
  --resource-group $RESOURCE_GROUP \
  --plan $APP_SERVICE_PLAN \
  --name $APP_SERVICE \
  --deployment-container-image-name $REGISTRY_NAME.azurecr.io/qamill:1.2.0

# Configure container
az webapp config container set \
  --name $APP_SERVICE \
  --resource-group $RESOURCE_GROUP \
  --docker-custom-image-name $REGISTRY_NAME.azurecr.io/qamill:1.2.0 \
  --docker-registry-server-url "https://$REGISTRY_NAME.azurecr.io" \
  --docker-registry-server-user $REGISTRY_USER \
  --docker-registry-server-password $REGISTRY_PASSWORD

# Set environment variables
az webapp config appsettings set \
  --resource-group $RESOURCE_GROUP \
  --name $APP_SERVICE \
  --settings \
    DATABASE_URL="postgresql://..." \
    REDIS_URL="redis://..." \
    WEBSITES_PORT=8765
```

---

## Custom Domain Setup

### Configure DNS

```bash
# Get your App Service IP or FQDN
az webapp show \
  --resource-group $RESOURCE_GROUP \
  --name $APP_SERVICE \
  --query "defaultHostName"

# Point your domain to Azure (configure in your DNS provider)
# CNAME: api.yourdomain.com -> qamill-app.azurewebsites.net

# Or use Azure DNS
az network dns zone create \
  --resource-group $RESOURCE_GROUP \
  --name yourdomain.com

az network dns record-set cname create \
  --resource-group $RESOURCE_GROUP \
  --zone-name yourdomain.com \
  --name api \
  --value qamill-app.azurewebsites.net
```

---

## SSL/TLS Certificate (HTTPS)

### Using Azure Key Vault

```bash
VAULT_NAME="qamill-vault"

# Create Key Vault
az keyvault create \
  --resource-group $RESOURCE_GROUP \
  --name $VAULT_NAME

# Create certificate (using Let's Encrypt via certbot)
certbot certonly --standalone -d api.yourdomain.com

# Import to Key Vault
az keyvault certificate import \
  --vault-name $VAULT_NAME \
  --name qamill-cert \
  --file /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem
```

---

## Monitoring & Logging

### Setup Application Insights

```bash
APP_INSIGHTS="qamill-insights"

# Create Application Insights
az monitor app-insights component create \
  --app $APP_INSIGHTS \
  --location $LOCATION \
  --resource-group $RESOURCE_GROUP \
  --application-type web

# Get instrumentation key
az monitor app-insights component show \
  --app $APP_INSIGHTS \
  --resource-group $RESOURCE_GROUP \
  --query "instrumentationKey"
```

### Configure Alerts

```bash
# Alert for high CPU usage
az monitor metrics alert create \
  --name "qamill-high-cpu" \
  --resource-group $RESOURCE_GROUP \
  --scopes /subscriptions/{subscription-id}/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.ContainerService/managedClusters/$CLUSTER_NAME \
  --condition "avg Percentage CPU > 80" \
  --window-size 5m \
  --evaluation-frequency 1m
```

---

## Backup & Disaster Recovery

### Database Backups

```bash
# Configure automated backups (7 days retention)
az postgres server update \
  --resource-group $RESOURCE_GROUP \
  --name $DB_SERVER \
  --backup-retention 7

# Create manual backup
az postgres server backup create \
  --name backup-$(date +%Y%m%d) \
  --resource-group $RESOURCE_GROUP \
  --server-name $DB_SERVER
```

### Storage Backups

```bash
# Enable blob soft delete
az storage blob service-properties delete-policy update \
  --account-name $STORAGE_ACCOUNT \
  --enable true \
  --days-retained 7
```

---

## Troubleshooting

### Check Pod Logs

```bash
# View logs
kubectl logs deployment/qamill-api -n qamill

# Follow logs
kubectl logs -f deployment/qamill-api -n qamill

# Check events
kubectl describe pod POD_NAME -n qamill
```

### Database Connection

```bash
# Test connection
psql -h $POSTGRES_URL -U $DB_USER -d qamill -c "SELECT 1"

# Or using Azure CLI
az postgres flexible-server connect \
  --name $DB_SERVER \
  --admin-user $DB_USER \
  --admin-password $DB_PASSWORD \
  --database-name qamill
```

### Redis Connection

```bash
# Test Redis
redis-cli -h $REDIS_HOST -a $REDIS_KEY ping
```

---

## Cost Optimization

### Scale Down Resources

```bash
# Scale AKS to 1 node for testing
az aks scale \
  --resource-group $RESOURCE_GROUP \
  --name $CLUSTER_NAME \
  --node-count 1

# Use B-series VMs for non-production
# Use Spot instances for batch processing
```

### Reserved Instances

```bash
# Purchase 1-year reserved instances for 30% savings
az reservations reservation create \
  --sku Standard_D2s_v3 \
  --scope /subscriptions/{subscription-id} \
  --term P1Y \
  --billing-plan Monthly
```

---

## CI/CD with Azure DevOps

### Create Pipeline

```yaml
# azure-pipelines.yml
trigger:
  - main

pool:
  vmImage: 'ubuntu-latest'

variables:
  dockerRegistryServiceConnection: 'qamill-acr'
  imageRepository: 'qamill'
  containerRegistry: 'qamillregistry.azurecr.io'

stages:
- stage: Build
  jobs:
  - job: Build
    steps:
    - task: Docker@2
      inputs:
        command: build
        repository: $(imageRepository)
        dockerfile: Dockerfile
        containerRegistry: $(dockerRegistryServiceConnection)
        tags: |
          $(Build.BuildId)
          latest

- stage: Deploy
  condition: eq(variables['Build.SourceBranch'], 'refs/heads/main')
  jobs:
  - deployment: Deploy
    environment: 'production'
    strategy:
      runOnce:
        deploy:
          steps:
          - task: KubernetesManifest@0
            inputs:
              action: 'deploy'
              kubeconnection: 'qamill-aks'
              namespace: 'qamill'
              manifests: |
                k8s-deployment.yaml
```

---

## Cleanup

### Remove All Resources

```bash
# Delete resource group (this removes everything)
az group delete \
  --name $RESOURCE_GROUP \
  --yes --no-wait

# Verify deletion
az group exists --name $RESOURCE_GROUP
```

---

## Complete Deployment Checklist

- [ ] Azure CLI installed and authenticated
- [ ] Resource group created
- [ ] ACR created and image pushed
- [ ] AKS cluster created
- [ ] PostgreSQL database created
- [ ] Redis cache created
- [ ] Storage account created
- [ ] Kubernetes secrets created
- [ ] Deployment applied to AKS
- [ ] Custom domain configured
- [ ] SSL certificate installed
- [ ] Application Insights enabled
- [ ] Monitoring alerts configured
- [ ] Backups enabled
- [ ] CI/CD pipeline configured

---

## Quick Reference

```bash
# Login
az login

# List resources
az resource list --resource-group qamill-prod

# Get connection strings
az postgres server show-connection-string --server-name qamill-postgres
az redis list-keys --resource-group qamill-prod --name qamill-redis

# Check deployment status
kubectl get all -n qamill

# View logs
kubectl logs deployment/qamill-api -n qamill
```

---

## Support Resources

- **Azure Documentation**: https://docs.microsoft.com/azure/
- **AKS Best Practices**: https://docs.microsoft.com/azure/aks/best-practices
- **Azure CLI Reference**: https://docs.microsoft.com/cli/azure/
- **Pricing Calculator**: https://azure.microsoft.com/pricing/calculator/

---

**QAMill is now ready to deploy on Azure!** 🚀

Choose your deployment option:
1. **AKS** (Recommended) - Full production-grade Kubernetes
2. **Container Instances** - Quick and simple
3. **App Service** - Easiest setup

Deploy with confidence! 🎉
