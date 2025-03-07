import json

class TenantConfigParser:
    def __init__(self, file_path):
        self.file_path = file_path
        self.config = None
        self.tenant = None

    def load_config(self):
        try:
            with open(self.file_path, 'r') as f:
                self.config = json.load(f)
        except Exception as e:
            raise RuntimeError(f"Failed to load config: {e}")

    def parse_config(self):
        if not self.config:
            raise RuntimeError("Config not loaded")

        imdata = self.config.get('imdata', [])
        if not imdata:
            raise RuntimeError("No data found in config")

        # Find the tenant directly under imdata (no polUni hierarchy)
        tenant_objects = [item for item in imdata if 'fvTenant' in item]
        if len(tenant_objects) != 1:
            raise RuntimeError(f"Expected 1 tenant, found {len(tenant_objects)}")

        tenant_data = tenant_objects[0]['fvTenant']
        self.tenant = {
            'name': tenant_data['attributes']['name'],
            'BDs': [],
            'VRFs': [],
            'L3Outs': []
        }

        # Parse tenant children
        for child in tenant_data.get('children', []):
            if 'fvBD' in child:
                self.tenant['BDs'].append(child['fvBD']['attributes'])
            elif 'fvCtx' in child:
                self.tenant['VRFs'].append(child['fvCtx']['attributes'])
            elif 'l3extOut' in child:
                self.tenant['L3Outs'].append(child['l3extOut']['attributes'])

    @property
    def bd_count(self):
        return len(self.tenant['BDs']) if self.tenant else 0

    @property
    def vrf_count(self):
        return len(self.tenant['VRFs']) if self.tenant else 0

    @property
    def l3out_count(self):
        return len(self.tenant['L3Outs']) if self.tenant else 0

# Usage example
if __name__ == '__main__':
    try:
        parser = TenantConfigParser(r'C:\Users\dsu979\OneDrive - dynexo GmbH\Desktop\APIC\APIC_Parser\tn-Migrate1.json')
        parser.load_config()
        parser.parse_config()

        print(f"Tenant Name: {parser.tenant['name']}")
        print(f"BD Count: {parser.bd_count}")
        print(f"VRF Count: {parser.vrf_count}")
        print(f"L3Out Count: {parser.l3out_count}")

    except Exception as e:
        print(f"Error: {str(e)}")