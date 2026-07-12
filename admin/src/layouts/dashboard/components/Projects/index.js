import { useEffect, useState, useMemo } from "react";
import { useDispatch, useSelector } from "react-redux";

// @mui material components
import Card from "@mui/material/Card";
import Icon from "@mui/material/Icon";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";

// PMS components
import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";

// PMS examples
import DataTable from "examples/Tables/DataTable";
// Data
import { centsToDollars } from "global/functions";

function Projects(props) {
  const [data1, setData] = useState({})

  useEffect(() => {
    setData(props.data);
  }, [props.data]);

  const data = useMemo(() => {
    return {
      columns: [
        {
          Header: "LicensePlate",
          accessor: "licensePlate",
          width: "30%",
          align: "left",
        },
        {
          Header: "No OF Bookings",
          accessor: "reservationCount",
          width: "40%",
          align: "left",
        },
        {
          Header: "Amount",
          accessor: "totalAmount",
          width: "30%",
          align: "center",
        },
      ],
      rows: Array.isArray(data1.topFive) && data1.topFive.length > 0 ?
        data1?.topFive.map((user, index) => ({
          licensePlate: (
            <MDBox display="flex" color="text.primary" py={1}>
              {user?._id?.licensePlate}
            </MDBox>
          ),
          reservationCount: (
            <MDTypography variant="caption" color="text.primary" fontWeight="medium">
              {user?.reservationCount}
            </MDTypography>
          ),
          totalAmount: (
            <MDBox width="8rem" textAlign="center">
              <MDTypography variant="caption" color="text.primary" fontWeight="medium">
                ${centsToDollars(user?.totalAmount || 0)}
              </MDTypography>
            </MDBox>
          ),
          key: index.toString(),
        })) : [],
    };
  }, [data1?.topFive]);

  const { columns, rows } = data;


  return (
    <Card>
      <MDBox
        display="flex"
        justifyContent="space-between"
        alignItems="center"
        p={3}
      >
        <MDBox>
          <MDTypography variant="h6" gutterBottom>
            Returning Users
          </MDTypography>
          <MDBox display="flex" alignItems="center" lineHeight={0}>
            <Icon
              sx={{
                fontWeight: "bold",
                color: ({ palette: { info } }) => info.main,
                mt: -0.5,
              }}
            >
              done
            </Icon>
            <MDTypography variant="button" fontWeight="regular" color="text">
              &nbsp;<strong>{data1?.totalCount} done</strong> this month
            </MDTypography>
          </MDBox>
        </MDBox>

      </MDBox>
      <MDBox>
        <DataTable
          table={{ columns, rows }}
          showTotalEntries={false}
          isSorted={false}
          noEndBorder
          entriesPerPage={false}
        />
      </MDBox>
    </Card>
  );
}

export default Projects;
