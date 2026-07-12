import MDButton from "components/MDButton";
import MDDialog from "components/MDDialog";
import MDTypography from "components/MDTypography";
import React from "react";
import { DialogContent, Grid, Divider } from "@mui/material";
import { useMaterialUIController } from "context";

const ConfirmationDialog = (props) => {
  const { dialogOpen, onClose, handelClick, title, description } = props;
  const [controller] = useMaterialUIController();
  const { sidenavColor } = controller;
  return (
    <>
      <MDDialog
        dialogTitle={title}
        open={dialogOpen}
        dialogClose={onClose}
        // closeIcon={true}
        maxWidth="sm"
      >
        <DialogContent sx={{ mt: 1, mb: 0 }}>
          <Grid container direction="column" spacing={1}>
            <Grid item>
              <MDTypography display="block" variant="subtitle2">
                {description}
              </MDTypography>
            </Grid>
            <Divider />
            <Grid item sx={{ display: "flex", justifyContent: "flex-end" }}>
              <MDButton variant="contained" size="small" onClick={onClose}>
                Cancel
              </MDButton>
              <MDButton
                color={sidenavColor}
                variant="contained"
                type="submit"
                onClick={handelClick}
                size="small"
              >
                Confirm
              </MDButton>
            </Grid>
          </Grid>
        </DialogContent>
      </MDDialog>
    </>
  );
};

export default ConfirmationDialog;
