
    part m0001_2N {

        part nx0001 {
            port scp_outside2;
        }

        part tcs0001{
            port scp;
        }

        interface tcs0001.scp to nx0001.scp_outside2;
    }
