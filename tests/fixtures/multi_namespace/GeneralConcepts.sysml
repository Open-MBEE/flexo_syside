package GeneralConcepts {
    private import ScalarValues::*;
    private import SI::*;
    private import USCustomaryUnits::*;
    package AttributeDeclarationExamples {
        attribute x1 : Integer = 1;
        attribute x2 : Real = 3.3;
        attribute x3 : Boolean = true;
        attribute x4 : String = "This is a String";
        attribute y1 :> length = 3.0 [m];
        attribute y2 :> mass = 100 [kg];
        attribute z1 :> length = 3.0 [ft];
        attribute z2 :> mass = 100 [lb];
    }
    package DefinitionAndUsageExample {
        part def Part0 {
            attribute x;
        }
        part def Part1 :> Part0 { // inherits x
            attribute x :>> x = 1;  // redefines x
            attribute y;           // adds y
        }
        part part1 :Part1; // inherits x,y;
        part part2 :Part1{ // inherits x,y{
            attribute y :>> y = 3; // redefines y
        }
        part part3 :> part2{ // inherits x, y
            attribute z [2];     // adds x [2]
        }
        part part4 :> part3{ // inherits x.y.z
            attribute x1 [1] :> x; // subsets x
            attribute x2 [1] :> x; // subsets x
        }
    }
}
