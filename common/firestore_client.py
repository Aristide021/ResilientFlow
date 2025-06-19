"""
Shared Firestore client for ResilientFlow inventory and cross-agent state management.
Handles resource tracking, allocation state, and agent coordination.
"""

import time
from typing import Dict, Any, Optional, List
from google.cloud import firestore
from google.cloud.firestore_v1 import FieldFilter, Query
from google.cloud.firestore_v1.base_query import BaseQuery

from .logging import get_logger, log_performance


class FirestoreClient:
    """Centralized Firestore client for agent state and inventory management"""
    
    def __init__(self, project_id: str, agent_name: str):
        self.project_id = project_id
        self.agent_name = agent_name
        self.logger = get_logger(agent_name)
        
        # Initialize Firestore client
        self.db = firestore.Client(project=project_id)
        
        # Collection references
        self.collections = {
            'inventory': self.db.collection('inventory'),
            'allocations': self.db.collection('allocations'),
            'agent_state': self.db.collection('agent_state'),
            'incidents': self.db.collection('incidents'),
            'facilities': self.db.collection('facilities'),
            'vehicles': self.db.collection('vehicles')
        }
    
    @log_performance("write_document")
    def write_document(self, collection: str, doc_id: str, data: Dict[str, Any], 
                      merge: bool = False) -> None:
        """Write document to specified collection"""
        
        if collection not in self.collections:
            raise ValueError(f"Unknown collection: {collection}")
        
        # Add metadata
        doc_data = {
            **data,
            'updated_by': self.agent_name,
            'updated_at': firestore.SERVER_TIMESTAMP
        }
        
        if not merge:
            doc_data['created_at'] = firestore.SERVER_TIMESTAMP
        
        # Write document
        doc_ref = self.collections[collection].document(doc_id)
        doc_ref.set(doc_data, merge=merge)
        
        self.logger.info(
            f"Wrote document {doc_id} to {collection}",
            collection=collection,
            document_id=doc_id,
            merge=merge
        )
    
    @log_performance("read_document")
    def read_document(self, collection: str, doc_id: str) -> Optional[Dict[str, Any]]:
        """Read document from specified collection"""
        
        if collection not in self.collections:
            raise ValueError(f"Unknown collection: {collection}")
        
        doc_ref = self.collections[collection].document(doc_id)
        doc = doc_ref.get()
        
        if doc.exists:
            return doc.to_dict()
        else:
            return None
    
    @log_performance("query_documents")
    def query_documents(self, collection: str, filters: List[tuple], 
                       order_by: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Query documents with filters"""
        
        if collection not in self.collections:
            raise ValueError(f"Unknown collection: {collection}")
        
        query = self.collections[collection]
        
        # Apply filters
        for field, operator, value in filters:
            query = query.where(filter=FieldFilter(field, operator, value))
        
        # Apply ordering
        if order_by:
            if order_by.startswith('-'):
                query = query.order_by(order_by[1:], direction=Query.DESCENDING)
            else:
                query = query.order_by(order_by, direction=Query.ASCENDING)
        
        # Apply limit
        if limit:
            query = query.limit(limit)
        
        # Execute query
        docs = query.stream()
        results = []
        
        for doc in docs:
            doc_data = doc.to_dict()
            doc_data['_id'] = doc.id
            results.append(doc_data)
        
        self.logger.debug(
            f"Queried {len(results)} documents from {collection}",
            collection=collection,
            filter_count=len(filters)
        )
        
        return results
    
    # Inventory Management
    
    def update_resource_inventory(self, resource_type: str, facility_id: str, 
                                 quantity: int, operation: str = 'set') -> Dict[str, Any]:
        """Update resource inventory at a facility"""
        
        inventory_id = f"{facility_id}_{resource_type}"
        
        if operation == 'set':
            inventory_data = {
                'resource_type': resource_type,
                'facility_id': facility_id,
                'quantity': quantity,
                'last_updated_ms': int(time.time() * 1000)
            }
            self.write_document('inventory', inventory_id, inventory_data, merge=True)
            
        elif operation in ['add', 'subtract']:
            # Use transaction for atomic updates
            @firestore.transactional
            def update_in_transaction(transaction, doc_ref):
                doc = doc_ref.get(transaction=transaction)
                current_quantity = 0
                
                if doc.exists:
                    current_quantity = doc.to_dict().get('quantity', 0)
                
                if operation == 'add':
                    new_quantity = current_quantity + quantity
                else:  # subtract
                    new_quantity = max(0, current_quantity - quantity)
                
                inventory_data = {
                    'resource_type': resource_type,
                    'facility_id': facility_id,
                    'quantity': new_quantity,
                    'last_updated_ms': int(time.time() * 1000),
                    'updated_by': self.agent_name
                }
                
                transaction.set(doc_ref, inventory_data, merge=True)
                return new_quantity
            
            doc_ref = self.collections['inventory'].document(inventory_id)
            transaction = self.db.transaction()
            new_quantity = update_in_transaction(transaction, doc_ref)
            
            self.logger.info(
                f"Updated inventory: {resource_type} at {facility_id}",
                operation=operation,
                quantity_change=quantity,
                new_quantity=new_quantity
            )
            
            return {
                'resource_type': resource_type,
                'facility_id': facility_id,
                'quantity': new_quantity
            }
        
        else:
            raise ValueError(f"Unknown operation: {operation}")
    
    def get_resource_availability(self, resource_type: Optional[str] = None, 
                                 facility_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get current resource availability"""
        
        filters = []
        
        if resource_type:
            filters.append(('resource_type', '==', resource_type))
        
        if facility_id:
            filters.append(('facility_id', '==', facility_id))
        
        # Only include resources with positive quantity
        filters.append(('quantity', '>', 0))
        
        return self.query_documents('inventory', filters, order_by='-last_updated_ms')
    
    # Allocation Management
    
    def create_allocation_plan(self, plan_id: str, incident_id: str, 
                              allocations: List[Dict[str, Any]]) -> None:
        """Create new resource allocation plan"""
        
        plan_data = {
            'plan_id': plan_id,
            'incident_id': incident_id,
            'allocations': allocations,
            'status': 'active',
            'created_ms': int(time.time() * 1000),
            'created_by': self.agent_name
        }
        
        self.write_document('allocations', plan_id, plan_data)
        
        self.logger.info(
            f"Created allocation plan {plan_id}",
            incident_id=incident_id,
            allocation_count=len(allocations)
        )
    
    def update_allocation_status(self, plan_id: str, allocation_id: str, 
                               status: str, notes: Optional[str] = None) -> None:
        """Update status of specific allocation within a plan"""
        
        plan = self.read_document('allocations', plan_id)
        if not plan:
            raise ValueError(f"Allocation plan {plan_id} not found")
        
        # Update allocation status
        allocations = plan.get('allocations', [])
        for allocation in allocations:
            if allocation.get('allocation_id') == allocation_id:
                allocation['status'] = status
                allocation['status_updated_ms'] = int(time.time() * 1000)
                allocation['status_updated_by'] = self.agent_name
                if notes:
                    allocation['notes'] = notes
                break
        
        # Write back updated plan
        plan['allocations'] = allocations
        self.write_document('allocations', plan_id, plan, merge=True)
    
    def get_active_allocations(self, incident_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all active allocation plans"""
        
        filters = [('status', '==', 'active')]
        
        if incident_id:
            filters.append(('incident_id', '==', incident_id))
        
        return self.query_documents('allocations', filters, order_by='-created_ms')
    
    # Agent State Management
    
    def update_agent_state(self, state_data: Dict[str, Any]) -> None:
        """Update agent's state information"""
        
        state_data.update({
            'agent_name': self.agent_name,
            'last_heartbeat_ms': int(time.time() * 1000)
        })
        
        self.write_document('agent_state', self.agent_name, state_data, merge=True)
    
    def get_agent_states(self) -> List[Dict[str, Any]]:
        """Get current state of all agents in the swarm"""
        
        # Get agents that have sent heartbeat in last 5 minutes
        five_min_ago = int(time.time() * 1000) - (5 * 60 * 1000)
        filters = [('last_heartbeat_ms', '>', five_min_ago)]
        
        return self.query_documents('agent_state', filters, order_by='-last_heartbeat_ms')
    
    # Facility and Vehicle Management
    
    def register_facility(self, facility_id: str, name: str, latitude: float, 
                         longitude: float, facility_type: str, capacity: Dict[str, int]) -> None:
        """Register a disaster relief facility"""
        
        facility_data = {
            'facility_id': facility_id,
            'name': name,
            'latitude': latitude,
            'longitude': longitude,
            'facility_type': facility_type,  # 'warehouse', 'hospital', 'shelter'
            'capacity': capacity,  # max capacity per resource type
            'status': 'operational'
        }
        
        self.write_document('facilities', facility_id, facility_data)
    
    def register_vehicle(self, vehicle_id: str, vehicle_type: str, capacity: int,
                        current_lat: float, current_lon: float, status: str = 'available') -> None:
        """Register a disaster relief vehicle"""
        
        vehicle_data = {
            'vehicle_id': vehicle_id,
            'vehicle_type': vehicle_type,  # 'truck', 'helicopter', 'boat'
            'capacity_kg': capacity,
            'current_latitude': current_lat,
            'current_longitude': current_lon,
            'status': status,  # 'available', 'deployed', 'maintenance'
            'last_position_update_ms': int(time.time() * 1000)
        }
        
        self.write_document('vehicles', vehicle_id, vehicle_data)
    
    def get_available_vehicles(self, vehicle_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of available vehicles"""
        
        filters = [('status', '==', 'available')]
        
        if vehicle_type:
            filters.append(('vehicle_type', '==', vehicle_type))
        
        return self.query_documents('vehicles', filters, order_by='capacity_kg')
    
    def get_facilities_near(self, latitude: float, longitude: float, 
                           max_distance_km: float = 50) -> List[Dict[str, Any]]:
        """Get facilities within specified distance (simplified - actual implementation would use GeoQuery)"""
        
        # This is a simplified implementation
        # In production, you'd use Firestore GeoQuery or BigQuery GIS
        all_facilities = self.query_documents('facilities', [])
        
        # Simple distance filter (in real implementation, use proper geo queries)
        nearby_facilities = []
        for facility in all_facilities:
            # Simple lat/lon distance approximation
            lat_diff = abs(facility['latitude'] - latitude)
            lon_diff = abs(facility['longitude'] - longitude)
            approx_distance = ((lat_diff ** 2 + lon_diff ** 2) ** 0.5) * 111  # rough km conversion
            
            if approx_distance <= max_distance_km:
                facility['distance_km'] = approx_distance
                nearby_facilities.append(facility)
        
        # Sort by distance
        nearby_facilities.sort(key=lambda x: x['distance_km'])
        return nearby_facilities 