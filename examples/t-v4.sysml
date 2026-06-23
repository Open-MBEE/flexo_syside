  package MyInterfaces {
  
    item def BudgetRequest;
    
    port def BuyerPort {
      out item request : BudgetRequest;
    }

    port def MarketPort {
      in item request : BudgetRequest;
    }

    interface def SearchFlow {

      flow of BudgetRequest
        from buyer.request
        to market.request;

      end buyer : BuyerPort;
      end market : MarketPort;
    }
  }