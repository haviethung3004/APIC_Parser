import json

class TenantConfigParser:
    def __init__(self, file_path):
        """
        Parser for single-tenant APIC configurations
        :param file_path: Path to tenant-specific JSON configuration
        """
        self.file_path = file_path
        self.config = None
        self.tenant = None  # Will hold the single tenant's configuration

    def load_config(self):
        """Load and validate JSON configuration"""
        try:
            with open(self.file_path, 'r') as file:
                self.config = json.load(file)
        except FileNotFoundError:
            raise Exception(f"Error: File '{self.file_path}' not found")
        except json.JSONDecodeError:
            raise Exception("Error: Invalid JSON format")

    def parse_config(self):
        """Parse the tenant configuration"""
        if not self.config:
            raise Exception("Configuration not loaded. Call load_config() first")

        # Navigate APIC's JSON structure
        imdata = self.config.get('imdata', [])
        if not imdata:
            raise Exception("Empty configuration file")

        pol_uni = imdata[0].get('polUni', {})
        tenant_node = self._find_tenant_node(pol_uni)

        # Parse tenant information
        self.tenant = self._parse_tenant_node(tenant_node)

    def _find_tenant_node(self, pol_uni):
        """Locate the single tenant node in configuration"""
        children = pol_uni.get('children', [])
        tenant_nodes = [child for child in children if 'fvTenant' in child]

        if len(tenant_nodes) != 1:
            raise Exception(f"Expected 1 tenant, found {len(tenant_nodes)}")
        
        return tenant_nodes[0]['fvTenant']

    def _parse_tenant_node(self, tenant_data):
        """Extract tenant information from configuration node"""
        tenant_info = {
            'name': tenant_data['attributes']['name'],
            'BDs': [],
            'VRFs': [],
            'L3Outs': []
        }

        # Process all child objects
        for obj in tenant_data.get('children', []):
            if 'fvBD' in obj:
                tenant_info['BDs'].append(obj['fvBD']['attributes'])
            elif 'fvCtx' in obj:
                tenant_info['VRFs'].append(obj['fvCtx']['attributes'])
            elif 'l3extOut' in obj:
                tenant_info['L3Outs'].append(obj['l3extOut']['attributes'])

        return tenant_info

    # Properties for easy access
    @property
    def bd_count(self):
        return len(self.tenant['BDs']) if self.tenant else 0

    @property
    def vrf_count(self):
        return len(self.tenant['VRFs']) if self.tenant else 0

    @property
    def l3out_count(self):
        return len(self.tenant['L3Outs']) if self.tenant else 0
    
if __name__ == "__main__":
    parser = TenantConfigParser(r'C:\Users\dsu979\OneDrive - dynexo GmbH\Desktop\APIC\APIC_Parser\tn-Migrate1.json')
    parser.load_config()
    parser.parse_config()

    print(f"Tenant Name: {parser.tenant['name']}")
    print(f"BD Count: {parser.bd_count}")
    print(f"VRF Count: {parser.vrf_count}")

    # Access specific BD attributes
    for bd in parser.tenant['BDs']:
        print(f"BD Name: {bd['name']}, ARP Flood: {bd.get('arpFlood', 'disabled')}")