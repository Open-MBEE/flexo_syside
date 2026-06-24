library package A {
    attribute def Orbit {
        attribute semiMajorAxis = 7000;

        attribute eccentricity = 0.01;

        attribute inclination = 28.5 {
            assert constraint { that >= 0.0 and that <= 90.0 }
        }

        attribute RAAN = 0.0; // Right Ascension of Ascending Node
        attribute argumentOfPeriapsis = 0.0;
        attribute trueAnomaly = 0.0;
    }
}

library package SDK {
    private import A::*;

    // structure

    port def P;

    part def S {
        port scp : P;
        attribute uid;
        attribute typeID;
    }

    part def N {
        port scp_outside2 : P;
        attribute uid;
    }

    part def M {
        attribute uid;
        part n : N [0..*];
        part s : S [0..*];
    }

    part def T :> S {
        attribute :>> typeID = 2;
    }
}

package M1 {
    private import SDK::*;

    part m0001_2N : M {
        attribute :>> uid = "M0001_2N";

        part nx0001 : N subsets n {
            attribute :>> uid = "NX0001";
        }

        part tcs0001 : T subsets s {
            attribute :>> uid = "TCS0001";
        }

        interface tcs0001.scp to nx0001.scp_outside2;
    }
}