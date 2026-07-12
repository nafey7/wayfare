import Dashboard from "layouts/dashboard";
import Profile from "layouts/profile";
import UserHistory from "layouts/my-users";
import Icon from "@mui/material/Icon";
import PriceChangeIcon from "@mui/icons-material/PriceChange";
import PricingPlans from "layouts/pricing-plans";
import Transactions from "layouts/transactions";
import Subscriptions from "layouts/subscriptions";
import AgentPrompts from "layouts/agent-prompts";
import EditAgentPrompt from "layouts/agent-prompts/edit";
const privateRoutes = [
  {
    type: "collapse",
    name: "Dashboard",
    key: "dashboard",
    icon: <Icon fontSize="small">dashboard</Icon>,
    route: "/dashboard",
    component: <Dashboard />,
  },
  {
    type: "collapse",
    name: "Pricing Plans",
    key: "pricing-plans",
    icon: (
      <Icon fontSize="small">
        <PriceChangeIcon />
      </Icon>
    ),
    route: "/pricing-plans",
    component: <PricingPlans />,
  },
  {
    type: "collapse",
    name: "Subscriptions",
    key: "subscriptions",
    icon: <Icon className="material-icons">subscriptions</Icon>,
    route: "/subscriptions",
    component: <Subscriptions />,
  },
  {
    type: "collapse",
    name: "Transactions",
    key: "transactions",
    icon: <Icon fontSize="small">account_balance</Icon>,
    route: "/transactions",
    component: <Transactions />,
  },

  {
    type: "collapse",
    name: "User Login History",
    key: "loginHistory",
    icon: <Icon fontSize="small">history</Icon>,
    route: "/login-history",
    component: <UserHistory />,
  },

  {
    type: "collapse",
    name: "AI Agent Prompts",
    key: "agent-prompts",
    icon: <Icon fontSize="small">smart_toy</Icon>,
    route: "/agent-prompts",
    component: <AgentPrompts />,
  },

  {
    type: "collapse",
    name: "Profile",
    key: "profile",
    icon: <Icon fontSize="small">person</Icon>,
    route: "/profile",
    component: <Profile />,
  },
];

// Additional routes that don't appear in sidebar
export const additionalRoutes = [
  {
    route: "/agent-prompts/:agentName",
    component: <EditAgentPrompt />,
  },
];

export default privateRoutes;
