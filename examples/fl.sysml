package FlashlightStarterModel {
  private import ScalarValues::*;
  private import SI::*;
  private import USCustomaryUnits::*;
  private import Definitions::*;
  package Definitions {
    item def OnOffCmd;
    attribute def DCPwr;
    item def Light;
  } // package Definitions
  package FlashlightSpecificationAndDesign {
    package Requirements {
      requirement flashlightSpecification {
        requirement userInterface;
        requirement illumination {
          requirement fieldOfView {
            doc
            /* The flashlight field of view shall be 0 - 20 degrees. */
          }
          requirement lightPower {
            doc
            /* The light power shall be a minumum of TBD lumens. */
          }
        }
        requirement physical {
          requirement portability;
          requirement size {
            doc
            /* The flashlight shall be less than 6 inches in length. */
          }
          requirement weight {
            doc
            /* The weight shall be less than 0.25 lbs. */
            attribute actualWeight :> ISQBase::mass;
            require constraint { actualWeight <= 0.25 ['pound (avoirdupois)'] }
          }
        }
        requirement reliability;
        requirement cost;
        requirement newRequirement;
      }
    } // package Requirements
    package Actions {
      action produceDirectedLight {
        in item onOffCmd;
        out item lightOut = directLight.lightOut;
        action provideDCPwr { out attribute dcPwr; }
        action connectDCPwr {
          in item onOffCmd;
          in attribute dcPwrIn;
          out attribute dcPwrOut;
        }
        action generateLight {
          in attribute dcPwrIn;
          out item light;
        }
        action directLight {
          in item lightIn;
          out item lightOut;
        }
        fork fork1;
          then provideDCPwr;
          then connectDCPwr;
        first Actions::Action::start then fork1;
        bind onOffCmd = connectDCPwr.onOffCmd;
        bind lightOut = directLight.lightOut;
        flow
          provideDCPwr.provideDCPwr::dcPwr
          to connectDCPwr.connectDCPwr::dcPwrIn;
        flow
          connectDCPwr.connectDCPwr::dcPwrOut
          to generateLight.generateLight::dcPwrIn;
        flow
          generateLight.generateLight::light
          to directLight.directLight::lightIn;
      }
    } // package Actions
    package Parts {
      part flashlight {
        attribute mass :> ISQBase::mass;
        attribute fov : Real;
        attribute illuminationLevel : Real;
        port cmdPort;
        port lightOutPort;
        port handPort;
        perform Actions::produceDirectedLight;
        exhibit state flashlightStates {
          state off;
          state on { do flashlight::produceDirectedLight; }
          transition off_To_on
            first off
            accept onOffCmd : Definitions::OnOffCmd via cmdPort
            then on;
          transition on_To_off
            first on
            accept onOffCmd : Definitions::OnOffCmd via cmdPort
            then off;
        }
        part battery [2] {
          port dcPwrOutPort {
            attribute v :> ISQElectromagnetism::voltage;
            out attribute i :> ISQBase::electricCurrent;
            out attribute dcPwr :> ISQMechanics::power = v * i;
          }
          perform produceDirectedLight.provideDCPwr;
        }
        part switch {
          port cmdPort;
          port inPort { in attribute dcPwrIn : Definitions::DCPwr; }
          port outPort { out attribute dcPwrOut : Definitions::DCPwr; }
          perform produceDirectedLight.connectDCPwr;
        }
        part lamp {
          attribute efficiency : Real;
          port dcPwrInPort { in attribute dcPwrIn : Definitions::DCPwr; }
          port lightOutPort { out item light : Definitions::Light; }
          perform produceDirectedLight.generateLight;
        }
        part optics {
          port lightInPort { in item light : Definitions::Light; }
          port lightOutPort { out item directedLight : Definitions::Light; }
          perform produceDirectedLight.directLight;
          part reflector { attribute radius :> ISQBase::length; }
          part lens;
        }
        part structure {
          port handPort;
          part frontHousing;
          part middleHousing;
          part backHousing;
        }
        bind cmdPort = switch.cmdPort;
        bind lightOutPort = optics.lightOutPort;
        bind handPort = structure.handPort;
        connect battery.dcPwrOutPort to switch.inPort {
          flow of Definitions::DCPwr
            from source.battery::dcPwrOutPort::dcPwr
            to target.switch::inPort::dcPwrIn;
        }
        connect switch.outPort to lamp.dcPwrInPort {
          flow of Definitions::DCPwr
            from source.switch::outPort::dcPwrOut
            to target.lamp::dcPwrInPort::dcPwrIn;
        }
        connect lamp.lightOutPort to optics.lightInPort {
          flow of Definitions::Light
            from source.lamp::lightOutPort::light
            to target.optics::lightInPort::light;
        }
      }
    } // package Parts
    package RequirementsAllocation {
      private import Requirements::*;
      private import Parts::*;
      allocate Requirements::flashlightSpecification to Parts::flashlight {
        allocate Requirements::flashlightSpecification.physical.weight
          to Parts::flashlight.mass;
        allocate Requirements::flashlightSpecification.illumination
          to Parts::flashlight.produceDirectedLight;
        allocate Requirements::flashlightSpecification.illumination.fieldOfView
          to Parts::flashlight.fov;
        allocate Requirements::flashlightSpecification.illumination.lightPower
          to Parts::flashlight.illuminationLevel;
      }
    } // package RequirementsAllocation
  } // package FlashlightSpecificationAndDesign
  package Analysis {
    calc def BatteryPower {
      in attribute voltage :> ISQElectromagnetism::voltage;
      in attribute current :> ISQBase::electricCurrent;
      attribute numberBatteriesInSeries : Integer default 2;
      return out power :> ISQMechanics::power =
        numberBatteriesInSeries * voltage * current;
    }
    attribute batteryPower :> ISQMechanics::power = BatteryPower(
      1.5 [volt],
      2.1 / 30 [ampere]
    );
    /* Note: current = currrent time (2.1 *3600 [A * s])/ battery life (30 *3600 [s]) */
  } // package Analysis
  package Verification {
    private import FlashlightSpecificationAndDesign::Requirements::*;
    private import FlashlightSpecificationAndDesign::Parts::*;
    public import VerificationCases::*;
    verification massTest {
      subject systemUnderTest
        :> FlashlightSpecificationAndDesign::Parts::flashlight;
      objective {
        doc
        /* Verify system under test satisfies its weight requirement */
        verify FlashlightSpecificationAndDesign::Requirements
              ::flashlightSpecification
              .physical.weight;
      }
      @VerificationMethod {
        ref VerificationMethod::kind = (
          VerificationMethodKind::test, VerificationMethodKind::analyze,
        );
      }
      action placeSystemOnScale;
      action weighSystem;
      action evaluateResult;
      action removeSystemFromScale;
    }
  } // package Verification
  package Views1 {
    private import Views::*;
    view flashlightPartsTree {
      expose FlashlightSpecificationAndDesign::Parts::**;
      filter @ SysML::Systems::PartUsage;
      render asTreeDiagram;
    }
  } // package Views1
} // package FlashlightStarterModel
package FlashlightContextClassExercise {
  private import FlashlightStarterModel::*;
  private import FlashlightStarterModel::Definitions::*;
  package ContextPkg_1 {
    package Requirements {
      requirement illuminationRequirement {
        doc
        /* Provide a capability for a user to illuminate their surrounding region */
      }
    } // package Requirements
    package Actions;
    package Parts;
  } // package ContextPkg_1
  package ContextPkg_2 {
    package Requirements {
      requirement illuminationRequirement {
        doc
        /* Provide a capability for a user to illuminate their surrounding region */
      }
    } // package Requirements
    package Actions;
    package Parts {
      part context {
        attribute illuminationArea;
        part user;
        part flashlight :> FlashlightSpecificationAndDesign::Parts::flashlight;
        part environment { part reflectingSource { attribute reflectivity; } }
      }
    } // package Parts
  } // package ContextPkg_2
  package ContextPkg_3 {
    package Requirements {
      requirement illuminationRequirement {
        doc
        /* Provide a capability for a user to illuminate their surrounding region */
      }
    } // package Requirements
    package Actions;
    package Parts {
      part context {
        attribute illuminationArea;
        part user {
          port p1 { out item onOffCmd; }
          port p2 { in item light; }
        }
        part flashlight :> FlashlightSpecificationAndDesign::Parts::flashlight {
          port cmdPort
            :>> FlashlightSpecificationAndDesign::Parts::flashlight::cmdPort {
            in item onOffCmd;
          }
          port lightOutPort
            :>>
              FlashlightSpecificationAndDesign::Parts::flashlight::lightOutPort {
            out item light;
          }
        }
        part environment {
          part reflectingSource {
            attribute reflectivity;
            port p1 { in item incidentLight; }
            port p2 { out item reflectedLight; }
          }
        }
        connect user.p1 to flashlight.cmdPort {
          flow of Definitions::OnOffCmd
            from source.user::p1::onOffCmd
            to target.flashlight::cmdPort::onOffCmd;
        }
        connect flashlight.lightOutPort to environment.reflectingSource.p1 {
          flow of Definitions::Light
            from source.flashlight::lightOutPort::light
            to target.environment::reflectingSource::p1::incidentLight;
        }
        connect environment.reflectingSource.p2 to user.p2 {
          flow of Definitions::Light
            from source.environment::reflectingSource::p2::reflectedLight
            to target.user::p2::light;
        }
      }
    } // package Parts
  } // package ContextPkg_3
  package ContextPkg_4 {
    package Requirements {
      requirement illuminationRequirement {
        doc
        /* Provide a capability for a user to illuminate their surrounding region */
      }
    } // package Requirements
    package Actions {
      action illuminateRegion {
        action turnLightOnOff;
        action produceDirectedLight
          :> FlashlightSpecificationAndDesign::Actions::produceDirectedLight;
        action reflectLight;
        action viewLight;
      }
    } // package Actions
    package Parts {
      part context {
        attribute illuminationArea;
        part user {
          port p1 { out item onOffCmd; }
          port p2 { in item light; }
        }
        part flashlight :> FlashlightSpecificationAndDesign::Parts::flashlight {
          port cmdPort
            :>> FlashlightSpecificationAndDesign::Parts::flashlight::cmdPort {
            in item onOffCmd;
          }
          port lightOutPort
            :>>
              FlashlightSpecificationAndDesign::Parts::flashlight::lightOutPort {
            out item light;
          }
        }
        part environment {
          part reflectingSource {
            attribute reflectivity;
            port p1 { in item incidentLight; }
            port p2 { out item reflectedLight; }
          }
        }
        connect user.p1 to flashlight.cmdPort {
          flow of Definitions::OnOffCmd
            from source.user::p1::onOffCmd
            to target.flashlight::cmdPort::onOffCmd;
        }
        connect flashlight.lightOutPort to environment.reflectingSource.p1 {
          flow of Definitions::Light
            from source.flashlight::lightOutPort::light
            to target.environment::reflectingSource::p1::incidentLight;
        }
        connect environment.reflectingSource.p2 to user.p2 {
          flow of Definitions::Light
            from source.environment::reflectingSource::p2::reflectedLight
            to target.user::p2::light;
        }
      }
    } // package Parts
  } // package ContextPkg_4
  package ContextPkg_5 {
    package Requirements {
      requirement illuminationRequirement {
        doc
        /* Provide a capability for a user to illuminate their surrounding region */
      }
    } // package Requirements
    package Actions {
      action illuminateRegion {
        action turnLightOnOff { out item onOffCmd; }
        action produceDirectedLight
          :> FlashlightSpecificationAndDesign::Actions::produceDirectedLight {
          in item onOffCmd
            :>>
              FlashlightSpecificationAndDesign::Actions::produceDirectedLight
              ::onOffCmd;
          out item lightOut
            :>>
              FlashlightSpecificationAndDesign::Actions::produceDirectedLight
              ::lightOut;
        }
        action reflectLight {
          in item incidentLight;
          out item reflectedLight;
        }
        action viewLight { in item light; }
        first Actions::Action::start then turnLightOnOff;
        flow
          turnLightOnOff.turnLightOnOff::onOffCmd
          to produceDirectedLight.produceDirectedLight::onOffCmd;
        flow
          produceDirectedLight.produceDirectedLight::lightOut
          to reflectLight.reflectLight::incidentLight;
        flow
          reflectLight.reflectLight::reflectedLight
          to viewLight.viewLight::light;
      }
    } // package Actions
    package Parts {
      part context {
        attribute illuminationArea;
        part user {
          port p1 { out item onOffCmd; }
          port p2 { in item light; }
        }
        part flashlight :> FlashlightSpecificationAndDesign::Parts::flashlight {
          port cmdPort
            :>> FlashlightSpecificationAndDesign::Parts::flashlight::cmdPort {
            in item onOffCmd;
          }
          port lightOutPort
            :>>
              FlashlightSpecificationAndDesign::Parts::flashlight::lightOutPort {
            out item light;
          }
        }
        part environment {
          part reflectingSource {
            attribute reflectivity;
            port p1 { in item incidentLight; }
            port p2 { out item reflectedLight; }
          }
        }
        connect user.p1 to flashlight.cmdPort {
          flow of Definitions::OnOffCmd
            from source.user::p1::onOffCmd
            to target.flashlight::cmdPort::onOffCmd;
        }
        connect flashlight.lightOutPort to environment.reflectingSource.p1 {
          flow of Definitions::Light
            from source.flashlight::lightOutPort::light
            to target.environment::reflectingSource::p1::incidentLight;
        }
        connect environment.reflectingSource.p2 to user.p2 {
          flow of Definitions::Light
            from source.environment::reflectingSource::p2::reflectedLight
            to target.user::p2::light;
        }
      }
    } // package Parts
  } // package ContextPkg_5
  package ContextPkg_6 {
    package Requirements {
      requirement illuminationRequirement {
        doc
        /* Provide a capability for a user to illuminate their surrounding region */
      }
    } // package Requirements
    package Actions {
      action illuminateRegion {
        action turnLightOnOff { out item onOffCmd; }
        action produceDirectedLight
          :> FlashlightSpecificationAndDesign::Actions::produceDirectedLight {
          in item onOffCmd
            :>>
              FlashlightSpecificationAndDesign::Actions::produceDirectedLight
              ::onOffCmd;
          out item lightOut
            :>>
              FlashlightSpecificationAndDesign::Actions::produceDirectedLight
              ::lightOut;
        }
        action reflectLight {
          in item incidentLight;
          out item reflectedLight;
        }
        action viewLight { in item light; }
        first Actions::Action::start then turnLightOnOff;
        flow
          turnLightOnOff.turnLightOnOff::onOffCmd
          to produceDirectedLight.produceDirectedLight::onOffCmd;
        flow
          produceDirectedLight.produceDirectedLight::lightOut
          to reflectLight.reflectLight::incidentLight;
        flow
          reflectLight.reflectLight::reflectedLight
          to viewLight.viewLight::light;
      }
    } // package Actions
    package Parts {
      part context {
        attribute illuminationArea;
        perform Actions::illuminateRegion;
        part user {
          port p1 { out item onOffCmd; }
          port p2 { in item light; }
          perform illuminateRegion.turnLightOnOff;
          perform illuminateRegion.viewLight;
        }
        part flashlight :> FlashlightSpecificationAndDesign::Parts::flashlight {
          port cmdPort
            :>> FlashlightSpecificationAndDesign::Parts::flashlight::cmdPort {
            in item onOffCmd;
          }
          port lightOutPort
            :>>
              FlashlightSpecificationAndDesign::Parts::flashlight::lightOutPort {
            out item light;
          }
          perform
            illuminateRegion.produceDirectedLight
            :>>
              FlashlightSpecificationAndDesign::Parts::flashlight
              ::produceDirectedLight;
        }
        part environment {
          perform illuminateRegion.reflectLight;
          part reflectingSource {
            attribute reflectivity;
            port p1 { in item incidentLight; }
            port p2 { out item reflectedLight; }
          }
        }
        connect user.p1 to flashlight.cmdPort {
          flow of Definitions::OnOffCmd
            from source.user::p1::onOffCmd
            to target.flashlight::cmdPort::onOffCmd;
        }
        connect flashlight.lightOutPort to environment.reflectingSource.p1 {
          flow of Definitions::Light
            from source.flashlight::lightOutPort::light
            to target.environment::reflectingSource::p1::incidentLight;
        }
        connect environment.reflectingSource.p2 to user.p2 {
          flow of Definitions::Light
            from source.environment::reflectingSource::p2::reflectedLight
            to target.user::p2::light;
        }
      }
    } // package Parts
  } // package ContextPkg_6
} // package FlashlightContextClassExercise
package GeneralConcepts {
  private import ScalarValues::*;
  private import SI::*;
  private import USCustomaryUnits::*;
  package AttributeDeclarationExamples {
    attribute x1 : Integer = 1;
    attribute x2 : Real = 3.3;
    attribute x3 : Boolean = true;
    attribute x4 : String = "This is a String";
    attribute y1 :> ISQBase::length = 3 [metre];
    attribute y2 :> ISQBase::mass = 100 [kilogram];
    attribute z1 :> ISQBase::length = 3 [foot];
    attribute z2 :> ISQBase::mass = 100 ['pound (avoirdupois)'];
  } // package AttributeDeclarationExamples
  package DefinitionAndUsageExample {
    part def Part0 { attribute x; }
    part def Part1 :> Part0 {
      attribute x :>> Part0::x = 1;
      attribute y;
    }
    part part1 : Part1;
    part part2 : Part1 { attribute y :>> Part1::y = 3; }
    part part3 :> part2 { attribute z [2]; }
    part part4 :> part3 {
      attribute x1 :> Part1::x [1];
      attribute x2 :> Part1::x [1];
    }
  } // package DefinitionAndUsageExample
} // package GeneralConcepts

