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
            }
            #mec part propulsionUnit {
                attribute :>> mass = 0.5 [SI::kg];
            }            
        }
    }

}