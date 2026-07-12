// @mui material components
import Card from "@mui/material/Card";
import Icon from "@mui/material/Icon";

// PMS components
import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";

// PMS example components
import TimelineItem from "examples/Timeline/TimelineItem";
import { useState, useEffect } from "react";

const colors = ["success", "error", "info", "warning", "primary"];
const icons = ["notifications", "inventory_2", "shopping_cart", "payment", "vpn_key"];
function OrdersOverview(props) {
  const [data, setData] = useState([])

  useEffect(() => {
    setData(props.data);
  }, [props.data]);

  return (
    <Card sx={{ height: "100%" }}>
      <MDBox pt={3} px={3}>
        <MDTypography variant="h6" fontWeight="medium">
          Top Selling Rates
        </MDTypography>
        <MDBox p={2}>
          {Array.isArray(data) && data.length > 0 ?
            data.map((item, index) => (
              <TimelineItem
                key={index}
                color={colors[index % colors.length]}
                icon={icons[index % icons.length]}
                title={item.displayName}
                dateTime={item.date}
                lastItem={index === data.length - 1}
              />
            ))
           : []}
        </MDBox>
      </MDBox>

    </Card>
  );
}

export default OrdersOverview;
