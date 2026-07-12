import { DialogContent, Divider, Grid } from "@mui/material";
import MDDialog from "components/MDDialog";
import MDBox from "components/MDBox";
import MDButton from "components/MDButton";
import { useMaterialUIController } from "context";
import MDTypography from "components/MDTypography";
// import {
//   deleteNotification,
//   getNotifications,
// } from "store/slice/notification/notificationSlice";
import { useDispatch } from "react-redux";

const NotificationDialog = (props) => {
  const { dialogOpen, onClose, data } = props;
  const [controller] = useMaterialUIController();
  const { sidenavColor } = controller;
  const apiDispatch = useDispatch();

  // const handleDelete = (id) => {
  //   apiDispatch(deleteNotification({ notificationId: id }))
  //     .unwrap()
  //     .then((res) => {
  //       const success = res?.success;
  //       if (success) {
  //         apiDispatch(getNotifications());
  //       }
  //     })
  //     .catch((err) => {
  //       console.error("Error creating pricing:", err);
  //     });
  //   onClose();
  // };

  return (
    <>
      <MDDialog
        dialogTitle={data?.title}
        open={dialogOpen}
        dialogClose={onClose}
        closeIcon={true}
        minWidth={"320px "}
        maxWidth={"350px "}
      >
        <DialogContent>
          <MDTypography display="block" variant="subtitle2" color="dark">
            {data?.message}
          </MDTypography>
          <Divider />
          <Grid item xs={12}>
            <MDBox display="flex" justifyContent="end">
              <MDButton
                color={sidenavColor}
                variant="contained"
                type="submit"
                // onClick={() => handleDelete(data?._id)}
              >
                Clear
              </MDButton>
            </MDBox>
          </Grid>
        </DialogContent>
      </MDDialog>
    </>
  );
};

export default NotificationDialog;
