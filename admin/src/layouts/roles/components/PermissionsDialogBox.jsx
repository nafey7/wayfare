import { DialogContent, Grid, Stack, Switch } from "@mui/material";
import MDBox from "components/MDBox";
import { useState } from "react";
import MDDialog from "components/MDDialog";
import MDSnackbar from "components/MDSnackbar";
import MDTypography from "components/MDTypography";
import CircularIndeterminate from "components/MDLoading";
import { isEmpty } from "lodash";
import MDBadge from "components/MDBadge";

const PermissionsDialogBox = (props) => {

  const { dialogOpen, onClose, PermissionsData = {} } = props;
  const [notification, setNotification] = useState({
    color: "",
    icon: "",
    title: "",
    content: "",
    show: false,
    close: () => setNotification({ ...notification, show: false }),
  });

  return (
    <>
      <CircularIndeterminate
        type="full"
        size={20}
        text="Creating role.. "
        open={false}
      />
      <MDSnackbar
        color={notification.color}
        icon={notification.icon}
        title={notification.title}
        content={notification.content}
        open={notification.show}
        close={notification.close}
        bgWhite
      />
      <MDDialog
        dialogTitle="Role Permissions"
        open={dialogOpen}
        dialogClose={onClose}
        closeIcon={true}
        maxWidth="sm"
      >
        <DialogContent>
          <Grid container spacing={2} className="mt-1">
            <Grid item xs={12}>
              {!isEmpty(PermissionsData) && (
                <Stack
                  direction="row"
                  className="gap-2 justify-content-between"
                >
                  <MDBox
                    className="flex-grow-1"
                    sx={{
                      "& :not(:first-of-type)": {
                        mb: 1.6,
                      },
                    }}
                  >
                    <MDTypography variant="h6" sx={{ mb: 1.3 }}>
                      Modules
                    </MDTypography>
                    {Object.keys(PermissionsData).map((key, index) => (
                      <MDTypography
                        variant="subtitle2"
                        gutterBottom
                        key={index}
                      >
                        {key.replace(/_/g, " ")}
                      </MDTypography>
                    ))}
                  </MDBox>
                  <MDBox className="flex-grow-1">
                    <MDTypography variant="h6" className="mb-1">
                      Permissions
                    </MDTypography>
                    {Object.keys(PermissionsData).map((key, index) => (
                      <Stack
                        direction="row"
                        className="gap-2 mx-2 justify-content-left align-items-center"
                        key={index}
                      >
                        <MDBadge
                          badgeContent={PermissionsData[key] ? "YES" : "NO"}
                          color={PermissionsData[key] ? "Primary" : "secondary"}
                          variant="gradient"
                          size="sm"
                        />
                        <Switch checked={PermissionsData[key]} />
                      </Stack>
                    ))}
                  </MDBox>
                </Stack>
              )}
            </Grid>
          </Grid>
        </DialogContent>
      </MDDialog>
    </>
  );
};

export default PermissionsDialogBox;
