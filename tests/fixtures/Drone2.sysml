package MechanicalObjectExample {
    private import ScalarValues::*;
    part def DroneSystem {
        part def Drone {
            part battery {
                /*attribute mass:ISQ::MassValue = 2.5 [SI::kg];*/
                attribute m:Real=2.5;
            }
            part propulsionUnit {
                attribute mass:ISQ::MassValue = 0.5 [SI::kg];
            }            
        }
    }

}