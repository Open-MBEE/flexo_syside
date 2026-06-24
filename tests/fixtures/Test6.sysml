package MechanicalObjectExample {
    abstract item def MechanicalObject {
        attribute mass :> ISQ::mass;
    }

    abstract item mechanicalObjects[*] : MechanicalObject;

    metadata def <mec> MechanicalObjectMetadata :> Metaobjects::SemanticMetadata {
        :>> baseType = mechanicalObjects meta SysML::Usage;
    }

    part def DroneSystem {
        part def Drone {
            #mec part battery {
                attribute :>> mass = 2.5 [SI::kg];
                item shape[1] : ShapeItems::Box :>> shape { 
                    attribute :>> length = 10 [SI::cm];
                    attribute :>> width = 4 [SI::cm];
                    attribute :>> height = 3 [SI::cm];
                }
            }
            #mec part propulsionUnit {
                attribute :>> mass = 0.5 [SI::kg];
                item shape[1] : ShapeItems::Cylinder :>> shape;
            }            
        }
    }

}