import { combineReducers } from "@reduxjs/toolkit";
import authReducers from "./slice/auth/authSlice";
import roleReducer from "./slice/roles/roleSlice";
import subscriptionReducer from "./slice/subscriptions/subscriptionSlice";
import dashboardReducer from "./slice/dashboard/dashboardSlice";
import pricingPlanReducer from "./slice/pricingPlan/pricingPlanSlice";
import transactionsReducer from "./slice/transactions/transactionSlice";

import userReducer from "./slice/users/userSlice";

const combinedReducer = combineReducers({
  auth: authReducers,
  roles: roleReducer,
  users: userReducer,
  subscriptions: subscriptionReducer,
  dashboard: dashboardReducer,
  pricingPlan: pricingPlanReducer,
  transactions: transactionsReducer,
});

export const rootReducer = (state, action) => {
  if (action.type === "auth/logout/fulfilled") {
    state = undefined;
  }
  return combinedReducer(state, action);
};
