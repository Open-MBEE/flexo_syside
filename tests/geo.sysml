
    part m0001_2N {

        part nx0001 {
            port scp_outside2;
        }

        part tcs0001{
            port scp;
        }

        interface tcs0001.scp to nx0001.scp_outside2;
    }

package MyStructureC {

    part def Component{
        attribute tx;
        attribute ty;
        attribute tz;

        attribute rx;
        attribute ry;
        attribute rz;

        attribute typeID;
        part children: Component[0..*];
    }

part def Solari {
}

part def PowerUnit :> Solari {
}

     part def Context {
        part myStructureC :Component {
            part nx0001g subsets children {
                attribute :>> tx=1.0;
                attribute :>> ty=1.0;
                attribute :>> tz=1.0;
                attribute :>> rx=1.0;
                attribute :>> ry=1.0;
                attribute :>> rz=1.0;
                attribute :>> typeID = 100;
                part pwr0001g:PowerUnit subsets children {
                    attribute :>> tx=1.0;
                    attribute :>> ty=2.0;
                    attribute :>> tz=1.0;
                    attribute :>> rx=1.0;
                    attribute :>> ry=2.0;
                    attribute :>> rz=1.0;
                    attribute :>> typeID = 0;
                }
                part cmp0001g subsets children {
                    attribute :>> tx=1.0;
                    attribute :>> ty=3.0;
                    attribute :>> tz=1.0;
                    attribute :>> rx=1.0;
                    attribute :>> ry=3.0;
                    attribute :>> rz=1.0;
                    attribute :>> typeID = 1;
                }
            }
            part nx0002g subsets children {
                attribute :>> tx=1.0;
                attribute :>> ty=1.0;
                attribute :>> tz=1.0;
                attribute :>> rx=1.0;
                attribute :>> ry=1.0;
                attribute :>> rz=1.0;
                attribute :>> typeID = 100;
                part pwr0002g subsets children {
                    attribute :>> tx=1.0;
                    attribute :>> ty=2.0;
                    attribute :>> tz=1.0;
                    attribute :>> rx=1.0;
                    attribute :>> ry=2.0;
                    attribute :>> rz=1.0;
                    attribute :>> typeID = 0;
                }
            }
        }
    }
}