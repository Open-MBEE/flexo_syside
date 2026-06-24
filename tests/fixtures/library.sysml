 package lpkg {
    part def A {
        port p;
    }
}

package pkg {
    private import lpkg::*;

    part a:A;
}