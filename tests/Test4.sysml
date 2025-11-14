package FlashlightStarterModel {
    package FlashlightSpecificationAndDesign {
        package Parts {
        }
    }
    package Views1{
        //private import Views::*;
        view flashlightPartsTree{
            expose FlashlightSpecificationAndDesign::Parts::**;
            filter @SysML::PartUsage;
            render Views::asTreeDiagram;
        }
    }
}

