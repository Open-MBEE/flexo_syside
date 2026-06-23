package FlashlightContextClassExercise{
    private import FlashlightStarterModel::*;
    private import FlashlightStarterModel::Definitions::*;
    package ContextPkg_1{
        package Requirements {
            requirement illuminationRequirement{
                doc /*Provide a capability for a user to illuminate their surrounding region*/
            }
        }
        package Actions{
        }
        package Parts{
        }  
    }
    package ContextPkg_2{
        package Requirements {
            requirement illuminationRequirement{
                doc /*Provide a capability for a user to illuminate their surrounding region*/
            }
        }
        package Actions{
        }
        package Parts{
            part context{
                attribute illuminationArea;
                part user;
                part flashlight :> FlashlightSpecificationAndDesign::Parts::flashlight;
                part environment {
                    part reflectingSource{
                        attribute reflectivity;
                    }
                }
            }
        }  
    }
    package ContextPkg_3{
        package Requirements {
            requirement illuminationRequirement{
                doc /*Provide a capability for a user to illuminate their surrounding region*/
            }
        }
        package Actions{
        }
        package Parts{
            part context{
                attribute illuminationArea;
                part user{
                    port p1 {
                        out item onOffCmd;
                    }
                    port p2 {
                        in item light;
                    }
                }
                part flashlight :> FlashlightSpecificationAndDesign::Parts::flashlight{
                    port cmdPort :>> cmdPort{
                        in item onOffCmd;
                    }
                    port lightOutPort :>> lightOutPort{
                        out item light;
                    }
                }
                part environment {
                    part reflectingSource{
                        attribute reflectivity;
                        port p1 {
                            in item incidentLight;
                        }
                        port p2 {
                            out item reflectedLight;
                        }
                    }
                }
                connect user.p1 to flashlight.cmdPort {
                    flow of OnOffCmd from source.onOffCmd to target.onOffCmd;
                }
                connect flashlight.lightOutPort to environment.reflectingSource.p1 {
                    flow of Light from source.light to target.incidentLight;
                }
                connect environment.reflectingSource.p2 to user.p2 {
                    flow of Light from source.reflectedLight to target.light;
                }
            }
        }  
    }
    package ContextPkg_4{
        package Requirements {
            requirement illuminationRequirement{
                doc /*Provide a capability for a user to illuminate their surrounding region*/
            }
        }
        package Actions{
            action illuminateRegion{
                action turnLightOnOff;
                action produceDirectedLight :> FlashlightSpecificationAndDesign::Actions::produceDirectedLight;
                action reflectLight;
                action viewLight;
            }
        }
        package Parts{
            part context{
                attribute illuminationArea;
                part user{
                    port p1 {
                        out item onOffCmd;
                    }
                    port p2 {
                        in item light;
                    }
                }
                part flashlight :> FlashlightSpecificationAndDesign::Parts::flashlight{
                    port cmdPort :>> cmdPort{
                        in item onOffCmd;
                    }
                    port lightOutPort :>> lightOutPort{
                        out item light;
                    }
                }
                part environment {
                    part reflectingSource{
                        attribute reflectivity;
                        port p1 {
                            in item incidentLight;
                        }
                        port p2 {
                            out item reflectedLight;
                        }
                    }
                }
                connect user.p1 to flashlight.cmdPort {
                    flow of OnOffCmd from source.onOffCmd to target.onOffCmd;
                }
                connect flashlight.lightOutPort to environment.reflectingSource.p1 {
                    flow of Light from source.light to target.incidentLight;
                }
                connect environment.reflectingSource.p2 to user.p2 {
                    flow of Light from source.reflectedLight to target.light;
                }
            }
        }  
    }
    package ContextPkg_5{
        package Requirements {
            requirement illuminationRequirement{
                doc /*Provide a capability for a user to illuminate their surrounding region*/
            }
        }
        package Actions{
            action illuminateRegion{
                action turnLightOnOff{
                    out item onOffCmd;
                }
                action produceDirectedLight :> FlashlightSpecificationAndDesign::Actions::produceDirectedLight{
                    in item onOffCmd :>> onOffCmd;
                    out item lightOut :>> lightOut;
                }
                action reflectLight{
                    in item incidentLight;
                    out item reflectedLight;
                }
                action viewLight{
                    in item light;
                }
                first start then turnLightOnOff;
                flow from turnLightOnOff.onOffCmd to produceDirectedLight.onOffCmd;
                flow from produceDirectedLight.lightOut to reflectLight.incidentLight;
                flow from reflectLight.reflectedLight to viewLight.light;
            }
        }
        package Parts{
            part context{
                attribute illuminationArea;
                part user{
                    port p1 {
                        out item onOffCmd;
                    }
                    port p2 {
                        in item light;
                    }
                }
                part flashlight :> FlashlightSpecificationAndDesign::Parts::flashlight{
                    port cmdPort :>> cmdPort{
                        in item onOffCmd;
                    }
                    port lightOutPort :>> lightOutPort{
                        out item light;
                    }
                }
                part environment {
                    part reflectingSource{
                        attribute reflectivity;
                        port p1 {
                            in item incidentLight;
                        }
                        port p2 {
                            out item reflectedLight;
                        }
                    }
                }
                connect user.p1 to flashlight.cmdPort {
                    flow of OnOffCmd from source.onOffCmd to target.onOffCmd;
                }
                connect flashlight.lightOutPort to environment.reflectingSource.p1 {
                    flow of Light from source.light to target.incidentLight;
                }
                connect environment.reflectingSource.p2 to user.p2 {
                    flow of Light from source.reflectedLight to target.light;
                }
            }
        }  
    }
    package ContextPkg_6{
        package Requirements {
            requirement illuminationRequirement{
                doc /*Provide a capability for a user to illuminate their surrounding region*/
            }
        }
        package Actions{
            action illuminateRegion{
                action turnLightOnOff{
                    out item onOffCmd;
                }
                action produceDirectedLight :> FlashlightSpecificationAndDesign::Actions::produceDirectedLight{
                    in item onOffCmd :>> onOffCmd;
                    out item lightOut :>> lightOut;
                }
                action reflectLight{
                    in item incidentLight;
                    out item reflectedLight;
                }
                action viewLight{
                    in item light;
                }
                first start then turnLightOnOff;
                flow from turnLightOnOff.onOffCmd to produceDirectedLight.onOffCmd;
                flow from produceDirectedLight.lightOut to reflectLight.incidentLight;
                flow from reflectLight.reflectedLight to viewLight.light;
            }
        }
        package Parts{
            part context{
                attribute illuminationArea;
                perform Actions::illuminateRegion;
                part user{
                    port p1 {
                        out item onOffCmd;
                    }
                    port p2 {
                        in item light;
                    }
                    perform illuminateRegion.turnLightOnOff;
                    perform illuminateRegion.viewLight;
                }
                part flashlight :> FlashlightSpecificationAndDesign::Parts::flashlight{
                    port cmdPort :>> cmdPort{
                        in item onOffCmd;
                    }
                    port lightOutPort :>> lightOutPort{
                        out item light;
                    }
                    perform illuminateRegion.produceDirectedLight :>> produceDirectedLight;
                }
                part environment {
                    perform illuminateRegion.reflectLight;
                    part reflectingSource{
                        attribute reflectivity;
                        port p1 {
                            in item incidentLight;
                        }
                        port p2 {
                            out item reflectedLight;
                        }
                    }
                }
                connect user.p1 to flashlight.cmdPort {
                    flow of OnOffCmd from source.onOffCmd to target.onOffCmd;
                }
                connect flashlight.lightOutPort to environment.reflectingSource.p1 {
                    flow of Light from source.light to target.incidentLight;
                }
                connect environment.reflectingSource.p2 to user.p2 {
                    flow of Light from source.reflectedLight to target.light;
                }
            }
        }  
    }
}

