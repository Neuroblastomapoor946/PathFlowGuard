@description('Resource location')
param location string = resourceGroup().location

@description('Prefix used for resource naming')
param namePrefix string = 'pathflowguard'

var storageName = toLower('${namePrefix}storage001')
var busName = toLower('${namePrefix}bus001')
var logName = '${namePrefix}-logs'
var envName = '${namePrefix}-env'
var keyVaultName = toLower('${namePrefix}kv001')

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logName
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
  }
}

resource serviceBus 'Microsoft.ServiceBus/namespaces@2022-10-01-preview' = {
  name: busName
  location: location
  sku: {
    name: 'Standard'
    tier: 'Standard'
  }
}

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  properties: {
    tenantId: subscription().tenantId
    sku: {
      family: 'A'
      name: 'standard'
    }
    enableRbacAuthorization: true
    publicNetworkAccess: 'Enabled'
  }
}

resource containerEnvironment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: envName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

output storageAccountName string = storage.name
output serviceBusNamespace string = serviceBus.name
output keyVaultResourceName string = keyVault.name
output containerAppsEnvironmentName string = containerEnvironment.name

