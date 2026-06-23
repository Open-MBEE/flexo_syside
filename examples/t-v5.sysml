package <TAILS_Model> 'TAILS – Tracking and Aerial Identification for Lost Species Model'{
  private import SYSMOD::*; 
  private import SystemCatalogue::**;
  
    alias SC for SystemCatalogue;
  occurrence def <TAILS_PRJ> 'TAILS Project' specializes SYSMOD::Project{
   concern :>> problemStatement{
    doc 
     /*There is a critical capability gap for a rapid, autonomous, and wide-area search solution that can operate
     * independently of ground barriers. To address this, a specialized drone system is required to locate and track lost
     *pets in real time. The system must overcome the challenges of navigating complex environments, identifying specific 
     *animals from the air using advanced computer vision, and tracking their movement without distressing the animal. By 
     *providing precise, actionable location data to owners and rescue teams, this system aims to drastically reduce 
     *search times, minimize animal exposure to danger, and increase successful recovery rates.
     */ 
    subject brownfieldSystem :> tailsBrownfieldContext.tailsSystemImpl :>> brownfieldSystem;
    stakeholder vince :>> projectOwner;
       //concern stakeholder needs
    part tailsSystemIdeaContext : IDEA::IDEA_CONTEXT :>> systemIdeaContext{
        part tailsSystem:>> tailsSystemIdeaContext::soi,IDEA::IDEA_CONTEXT::tailsSystem;
    }
    part tailsSpecificationContext : SPEC::SPEC_CONTEXT :> specificationContext{ 
       part tails :>> tailsSystem, systemOfInterest;

       }
    
   }
    part tailsBrownfieldContext: BA::BA_CONTEXT :>> brownfieldSystemContext;
  }
 
  package<BA> 'TAILS Brownfield Architecture'{
    part def <BA_SYSTEM> 'TAILS Brownfield System' {
      port operatorPort: SC::Interfaces::OperatorPort;
    }
    part def <BA_SYSTEM_IMPL> 'TAILS Brownfield System Implementation' :> BA_SYSTEM {
      part drones {
        part engines [4..8] : Engine;
        part battery [1..2] : Battery;
        part body : Body;
        interface power : PowerDistribution
          connect battery.energyOutPort to engines.energyPort;
      }
      part controlStation{
        port operatorPort: OperatorPort;
      }
      bind operatorPort = controlStation.operatorPort;
    }
  
  
    part def <BA_CONTEXT> 'TAILS Brownfield Context' specializes SYSMOD::SystemContext {
        part tailsSystem : BA_SYSTEM :>> soi {
          port :>> operatorPort:> systemPorts;
        }
        part tailsSystemImpl: BA_SYSTEM_IMPL :> tailsSystem :>> soiImpl;
        interface operatorIF :> act2sys
          connect operator.operatorPort to tailsSystem.operatorPort;
        part environment : Environment :> actors {
          port:>> environmentPort, actorPort;
        }
        part operator : Operator :> actors {
          port :>> operatorPort, actorPort;
        }
        partlandingZone: LandingZone:> actors {
          port:>> zonePort, actorPort;
        }
        partloadingAgent:> actors;
        }
    }
        //Project Idea
    package <IDEA> tailsSystem_SystemIdea{
        part def <IDEA_CONTEXT> tailsSystem_SystemIdeaContext:> BA::BA_CONTEXT{
            part tailsSystem: IDEA_SYSTEM :>> tailsSystem;
        }
        part def <IDEA_SYSTEM> TAILSSystem_SystemIdea:> BA::BA_SYSTEM_IMPL {
            doc/* "Every year, millions of pets go missing, leaving owners helpless against vast search areas and treacherous ground barriers. 
                To bridge this critical gap, we are evolving the baseline TAILS Brownfield System into an autonomous, wide-area search and tracking solution. 
                By upgrading the core multi-engine drone platform with advanced computer vision and specialized payload sensors,
                the system can autonomously navigate complex environments to identify specific lost animals from the air.
                Utilizing real-time data streaming through the established control station interface, 
                it provides rescue teams and owners with precise location tracking without causing distress to the animal. 
                Ultimately, this system transforms existing hardware into a rapid-response lifesaver, 
                dramatically reducing search times and maximizing successful pet recoveries." */
            part :>> drones {
                part engines[4..6] :>> engines;
                part sensors [1..4] : Sensor;
                part communication : CommunicationSystem;
                part advprocessor : Computer;
            }
        }
    }
    package <SPEC> tails_Specification {
        
      package <UC> {
          use case def ExecuteAutonomousSearchMission {
              subject system : SPEC::SPEC_SYSTEM;
              actor operator;
              actor animalSpotter;
              actor grappleOperater;
              objective {
                  doc /* Area search mission to find, track and retrieve lost pets. */
              }
              first start then launchtails;
              first launchtails then flysearchmission;
              first flysearchmission then acquirepet;
              first acquirepet then retrievepet;
              first retrievepet then returntostation;
              first returntostation then done;
              action launchtails;
              action flysearchmission;
              action acquirepet;
              action retrievepet;
              action returntostation;
          }
      }
    part def <SPEC_SYSTEM> TailsSystemSpecificationSystem :> IDEA::IDEA_SYSTEM {
          action launchtails;
          action flysearchmission;
          action acquirepet;
          action retrievepet;
          action returntostation;
      } 
      #systemContext part def<SPEC_CONTEXT> DeliveryDroneSystemSpecificationContext :> IDEA::IDEA_CONTEXT {
          part tailsSystem: SPEC_SYSTEM :>> tailsSystem;
          part missionPlanner:> actors;
          use case executeAutonomousSearchMission : UC::ExecuteAutonomousSearchMission{
              subject :>> system :> tailsSystem;
              actor :>> operator ;
              actor animalSpotter;
              actor grappleOperater;
          }

      }

    }
}