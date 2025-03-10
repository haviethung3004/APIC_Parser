"""
Data models for ACI objects
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

@dataclass
class ACIAttribute:
    """Class to represent an ACI object attribute"""
    name: str
    value: Any
    description: Optional[str] = None


@dataclass
class ACIObject:
    """Class to represent an ACI object"""
    class_name: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    children: List['ACIObject'] = field(default_factory=list)
    path: Optional[str] = None
    
    @property
    def name(self) -> Optional[str]:
        """Get the name attribute if available"""
        return self.attributes.get('name')
    
    @property
    def description(self) -> Optional[str]:
        """Get the description attribute if available"""
        return self.attributes.get('descr')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        result = {
            self.class_name: {
                "attributes": self.attributes,
            }
        }
        
        if self.children:
            result[self.class_name]["children"] = [
                child.to_dict() for child in self.children
            ]
            
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ACIObject':
        """Create an ACIObject from dictionary representation"""
        if not data:
            raise ValueError("Input data cannot be empty")
            
        # Get the class name (first key)
        if len(data) != 1:
            raise ValueError(f"Expected a single class key, got {len(data)}")
            
        class_name = list(data.keys())[0]
        class_data = data[class_name]
        
        # Extract attributes and children
        attributes = class_data.get("attributes", {})
        
        # Create the object
        obj = cls(
            class_name=class_name,
            attributes=attributes
        )
        
        # Process children if any
        children_data = class_data.get("children", [])
        for child_dict in children_data:
            child = cls.from_dict(child_dict)
            obj.children.append(child)
            
        return obj


@dataclass
class TenantConfig:
    """Class to represent a tenant configuration"""
    tenant_name: str
    tenant_dn: str
    objects: List[ACIObject] = field(default_factory=list)
    
    @classmethod
    def from_json(cls, config: Dict[str, Any]) -> 'TenantConfig':
        """Create a TenantConfig from JSON data"""
        if 'imdata' not in config or not config['imdata']:
            raise ValueError("Expected 'imdata' key in configuration")
            
        # Get the first object (typically the tenant)
        tenant_data = config['imdata'][0]
        if not tenant_data:
            raise ValueError("No tenant data found")
            
        tenant_class = list(tenant_data.keys())[0]
        tenant_attributes = tenant_data[tenant_class].get('attributes', {})
        
        # Create the tenant config
        tenant_config = cls(
            tenant_name=tenant_attributes.get('name', 'Unknown'),
            tenant_dn=tenant_attributes.get('dn', '')
        )
        
        # Process children
        children = tenant_data[tenant_class].get('children', [])
        for child_dict in children:
            child = ACIObject.from_dict(child_dict)
            tenant_config.objects.append(child)
            
        return tenant_config