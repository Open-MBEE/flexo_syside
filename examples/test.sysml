package P1 {
    // private import ScalarValues::Integer;

    part def Component{
        attribute id;
        part children: Component[0..*];
    }

    
    part def p1 {
//        attribute a1: Integer = 9999;
        attribute a1 = 9999;
        attribute a2 = a1 + 1;
    }
}