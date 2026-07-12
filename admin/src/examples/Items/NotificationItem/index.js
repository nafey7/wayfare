// /**
// =========================================================
// * PMS - v2.2.0
// =========================================================

// * Product Page: https://www.creative-tim.com/product/material-dashboard-react
// * Copyright 2023 Creative Tim (https://www.creative-tim.com)

// Coded by www.creative-tim.com

//  =========================================================

// * The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
// */

// import { forwardRef, useEffect, useState } from "react";

// // prop-types is a library for typechecking of props.
// import PropTypes from "prop-types";

// // @mui material components
// import MenuItem from "@mui/material/MenuItem";
// import Link from "@mui/material/Link";

// // PMS components
// import MDBox from "components/MDBox";
// import MDTypography from "components/MDTypography";

// // custom styles for the NotificationItem
// import menuItem from "examples/Items/NotificationItem/styles";
// import { Message } from "rsuite";

// import { formattedDateWithTime } from "global/functions";
// import { readNotification } from "store/slice/notification/notificationSlice";
// import { useDispatch } from "react-redux";

// const NotificationItem = forwardRef(
//   ({ icon, data, openMsgDialog, ...rest }, ref) => {
//     const apiDispatch = useDispatch();

//     const handleRead = (id) => {
//       apiDispatch(readNotification({ notificationId: id }));
//     };

//     return (
//       <MenuItem
//         {...rest}
//         ref={ref}
//         sx={(theme) => menuItem(theme)}
//         onClick={() => openMsgDialog(data)}
//       >
//         <MDBox
//           component={Link}
//           py={0.5}
//           display="flex"
//           alignItems="center"
//           lineHeight={1}
//         >
//           <MDTypography variant="body1" color="secondary" lineHeight={0.75}>
//             {icon}
//           </MDTypography>
//           <MDTypography variant="button" fontWeight="regular" sx={{ ml: 1 }}>
//             {data?.message?.length > 26
//               ? `${data?.message?.slice(0, 26)}...`
//               : data?.message}
//           </MDTypography>
//           {openMsgDialog && (
//             <MDTypography variant="button" fontWeight="regular" sx={{ ml: 1 }}>
//               {formattedDateWithTime(data?.createdAt)}
//             </MDTypography>
//           )}
//         </MDBox>
//         {openMsgDialog && (
//           <button onClick={() => handleRead(data?._id)}>Mark as read</button>
//         )}
//       </MenuItem>
//     );
//   }
// );

// // Typechecking props for the NotificationItem
// NotificationItem.propTypes = {
//   icon: PropTypes.node.isRequired,
//   title: PropTypes.string.isRequired,
// };

// export default NotificationItem;

import { forwardRef } from "react";
import PropTypes from "prop-types";
import Link from "@mui/material/Link";
import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import menuItem from "examples/Items/NotificationItem/styles";
import { formattedDateWithTime } from "global/functions";
// import {
//   readNotification,
//   getNotifications,
// } from "store/slice/notification/notificationSlice";
import { useDispatch } from "react-redux";
import { Grid, Card, MenuItem } from "@mui/material";
import MDAvatar from "components/MDAvatar";

const NotificationItem = forwardRef(
  ({ icon, data, openMsgDialog, ...rest }, ref) => {
    const apiDispatch = useDispatch();

    // const handleRead = (data) => {
    //   openMsgDialog(data);

    //   if (data?.readStatus !== "read") {
    //     apiDispatch(readNotification({ notificationId: data?._id }))
    //       .unwrap()
    //       .then((res) => {
    //         const success = res?.success;
    //         if (success) {
    //           apiDispatch(getNotifications());
    //         }
    //       })
    //       .catch((err) => {
    //         console.error("Error creating pricing:", err);
    //       });
    //   }
    // };
    return (
      <MenuItem
        {...rest}
        ref={ref}
        sx={(theme) => ({
          ...menuItem(theme),
          padding: "4px 5px",
        })}
        // onClick={() => handleRead(data)}
      >
        <MDBox
          display="flex"
          justifyContent="space-between"
          alignItems="center"
          width="100%"
        >
          <Card sx={{ boxShadow: 3, width: "230px" }}>
            <MDBox p={1}>
              <Grid container spacing={1}>
                <Grid item xs={12}>
                  <MDBox
                    mt={1}
                    display="flex"
                    justifyContent="flex-start"
                    alignItems="center"
                  >
                    <MDBox
                      display="flex"
                      flexDirection="row"
                      justifyContent="center"
                      alignItems="center"
                    >
                      <MDBox sx={{ height: "25px" }}>
                        {data?.brandLogo ? (
                          <img
                            src={data?.brandLogo}
                            alt="brand"
                            style={{
                              width: "25px",
                              height: "25px",
                              objectFit: "contain",
                              backgroundColor: "#FAF9F6",
                              borderRadius: "100%",
                            }}
                          />
                        ) : (
                          <MDAvatar sx={{width: '25px', height: '25px'}} size="sm" shadow="sm" />
                        )}
                      </MDBox>

                      <MDTypography
                        sx={{ paddingLeft: "5px" }}
                        variant="subtitle"
                        fontWeight="bold"
                        color="dark"
                      >
                        {data?.brandName ? data?.brandName : "Super Admin"}
                      </MDTypography>
                    </MDBox>
                  </MDBox>
                </Grid>

                <Grid item xs={12}>
                  <MDTypography
                    color="dark"
                    display="block"
                    variant="subtitle"
                    sx={{ flex: 1 }}
                  >
                    {data?.title}
                  </MDTypography>
                </Grid>

                <Grid
                  display="flex"
                  justifyContent="flex-end"
                  alignItems="center"
                  item
                  xs={12}
                >
                  <MDTypography variant="subtitle" sx={{fontSize: '10px'}}>
                    {formattedDateWithTime(data?.createdAt)}
                  </MDTypography>
                </Grid>
              </Grid>
            </MDBox>
          </Card>

          <div
            style={{
              width: "12px",
              height: "12px",
              borderRadius: "100%",
              backgroundColor: data?.readStatus !== "read" && "blue",
              border: "2px solid blue",
            }}
          ></div>
        </MDBox>
      </MenuItem>
    );
  }
);

// Typechecking props for the NotificationItem
NotificationItem.propTypes = {
  icon: PropTypes.node.isRequired,
  data: PropTypes.object.isRequired,
  openMsgDialog: PropTypes.func.isRequired,
};

export default NotificationItem;
