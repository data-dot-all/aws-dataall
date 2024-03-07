export const AwsRegions = [
  { name: 'US East (Ohio)', code: 'us-east-2' },
  { name: 'US East (N. Virginia)', code: 'us-east-1' },
  { name: 'US West (N. California)', code: 'us-west-1' },
  { name: 'US West (Oregon)', code: 'us-west-2' },
  { name: 'Africa (Cape Town)', code: 'af-south-1' },
  { name: 'Asia Pacific (Hong Kong)', code: 'ap-east-1' },
  { name: 'Asia Pacific (Mumbai)', code: 'ap-south-1' },
  { name: 'Asia Pacific (Osaka-Local)', code: 'ap-northeast-3' },
  { name: 'Asia Pacific (Seoul)', code: 'ap-northeast-2' },
  { name: 'Asia Pacific (Singapore)', code: 'ap-southeast-1' },
  { name: 'Asia Pacific (Sydney)', code: 'ap-southeast-2' },
  { name: 'Asia Pacific (Tokyo)', code: 'ap-northeast-1' },
  { name: 'Canada (Central)', code: 'ca-central-1' },
  { name: 'China (Beijing)', code: 'cn-north-1' },
  { name: 'China (Ningxia)', code: 'cn-northwest-1' },
  { name: 'Europe (Frankfurt)', code: 'eu-central-1' },
  { name: 'Europe (Ireland)', code: 'eu-west-1' },
  { name: 'Europe (London)', code: 'eu-west-2' },
  { name: 'Europe (Milan)', code: 'eu-south-1' },
  { name: 'Europe (Paris)', code: 'eu-west-3' },
  { name: 'Europe (Stockholm)', code: 'eu-north-1' },
  { name: 'Middle East (Bahrain)', code: 'me-south-1' },
  { name: 'South America (São Paulo)', code: 'sa-east-1' },
  { name: 'AWS GovCloud (US-East)', code: 'us-gov-east-1' },
  { name: 'AWS GovCloud (US)', code: 'us-gov-west-1' }
];

export const regexToValidateWindowPathName = /^[a-zA-Z0-9/]*$/