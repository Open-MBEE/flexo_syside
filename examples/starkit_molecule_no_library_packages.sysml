package Starkit_AlgoDomain {
    private import ScalarValues::*;
    private import ISQ::*;
    private import SI::*;

    attribute def Orbit {
        attribute semiMajorAxis:> ISQ::length = 7000 [SI::km];
        attribute eccentricity: ScalarValues::Real = 0.01;
        attribute inclination:ScalarValues::Real = 28.5 [SI::degree] {
            assert constraint { that >= 0.0 and that <= 90.0 }
        }

        attribute RAAN:ScalarValues::Real = 0.0 [SI::degree];  // Right Ascension of Ascending Node
        attribute argumentOfPeriapsis:ScalarValues::Real = 0.0 [SI::degree];
        attribute trueAnomaly:ScalarValues::Real = 0.0 [SI::degree];
    }

    attribute def PlanetModel {
        attribute planet_albedo: ScalarValues::Real;
        attribute planet_emissivity: ScalarValues::Real;
        attribute planet_temperature:> ISQ::temperature = 0 [SI::K];
    // at 1 AU
        attribute solar_constant: ScalarValues::Real;
    }

    attribute def Shadows{
        attribute prenumbra_entry: ScalarValues::Real;
        attribute prenumbra_exit: ScalarValues::Real;
        attribute numbra_entry: ScalarValues::Real;
        attribute numbra_exit: ScalarValues::Real;
        assert constraint {prenumbra_entry < numbra_entry}
    }
}

package Starkit {
    private import ScalarValues::*;
    private import ISQ::*;
    private import SI::*;
    private import Starkit_AlgoDomain::*;

// structure
    port def ServiceConnectionPoint;
    port def N2N;

    part def Solari {
        port scp : ServiceConnectionPoint;
        attribute uid;
        attribute typeID;
    }
    part def Nexus {
        port scp_inside1 : ServiceConnectionPoint;
        port scp_inside2 : ServiceConnectionPoint;
        port scp_inside3 : ServiceConnectionPoint;
        port scp_inside4 : ServiceConnectionPoint;
        port scp_inside5 : ServiceConnectionPoint;
        port scp_inside6 : ServiceConnectionPoint;
        port scp_inside7 : ServiceConnectionPoint;
        port scp_outside1 : ServiceConnectionPoint;
        port scp_outside2 : ServiceConnectionPoint;
        port scp_outside3 : ServiceConnectionPoint;
        port scp_outside4 : ServiceConnectionPoint;
        port scp_outside5 : ServiceConnectionPoint;
        port scp_outside6 : ServiceConnectionPoint;
        port scp_outside7 : ServiceConnectionPoint;
        port bottom : N2N;
        port top : N2N;
        attribute uid;
    }
    part def Molecule {
        attribute uid;
        part nexus: Nexus[0..*];
        part solari: Solari[0..*];
    }

    part def PowerUnit :> Solari {
        attribute :>> typeID = 0;
    }

    part def ThrusterSolari :> Solari {}

    part def HIPARC :> ThrusterSolari {
        attribute :>> typeID = 14;
    }
    part def BHT40 :> ThrusterSolari {
        attribute :>> typeID = 15;
    }
    part def Battery :> Solari {
        attribute :>> typeID = 1;
    }
    part def ThermalUnit :> Solari {
        attribute :>> typeID = 2;
    }
    part def Communication :> Solari {
        attribute :>> typeID = 4;
    }
    part def Attitude :> Solari {
        attribute :>> typeID = 4;
    }
    part def PayloadInside :> Solari {
        attribute :>> typeID = 9;
    }
    part def PayloadOutside :> Solari {
        attribute :>> typeID = 10;
    }
    part def FuelTankInside :> Solari {
        attribute :>> typeID = 16;
    }
    part def FuelTankOutside :> Solari {
        attribute :>> typeID = 17;
    }
    part def Compute :> Solari {
        attribute :>> typeID = 5;
    }
    part def Transporter :> Solari {
        attribute :>> typeID = 6;
    }
    part def TripleRadiator :> Solari {
        attribute :>> typeID = 11;
    }

    part def ElectronicBox;
    part def HeatExchanger;
    part def Radiator;

// behavior
    action def add_nexus {
        in part mIn : Molecule;
        in part nIn : Nexus;
        out part mOut : Molecule;
    }

    action def add_solari {
        in part mIn : Molecule;
        in part nIn : Nexus;
        in part sIn : Solari;
        in attribute pos : Integer;
        out part mOut : Molecule;
    }

    action def move_solari {
        in part mIn : Molecule;
        in part sIn : Solari;
        in part destNexus : Nexus;
        in attribute destPos : Integer;
        out part mOut : Molecule;
    }
    
    action def calculate_total_mass {
        in part mIn: Molecule;
        out attribute total_mass: ISQ::MassValue;
    }

    action def calculate_total_power {
        in part mIn: Molecule;
        out attribute total_mass: ISQ::PowerValue;
    }

    action def change_radiator_angle {
        in part mIn: Molecule;
        in part thIn: ThermalUnit;
        in attribute deploy_angle: ScalarValues::Real=0.0 [SI::degree];
        in attribute rot_angle: ScalarValues::Real=0.0 [SI::degree];
    }
}


package Molecule {
    private import Starkit::*;

    part m0001_2N : Molecule {
        attribute :>> uid = "M0001_2N";
        part nx0001 : Nexus subsets nexus {
            attribute :>> uid = "NX0001";
        }
        part com0001 : Communication subsets solari {
            attribute :>> uid = "COM0001";
        }
        part tcs0001 : ThermalUnit subsets solari {
            attribute :>> uid = "TCS0001";
        }
        part att0001 : Attitude subsets solari {
            attribute :>> uid = "ATT0001";
        }
        part cmp0001 : Compute subsets solari {
            attribute :>> uid = "CMP0001";
        }
        interface com0001.scp to nx0001.scp_inside5;
        interface tcs0001.scp to nx0001.scp_outside2;
        interface att0001.scp to nx0001.scp_outside4;
        interface cmp0001.scp to nx0001.scp_outside7;
    }
}
