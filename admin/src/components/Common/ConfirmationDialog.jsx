import React from "react";

import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import Slide from "@mui/material/Slide";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import MDDialog from "components/MDDialog";
import MDTextButton from "components/MDTextButton";
import MDButton from "components/MDButton";

const Transition = React.forwardRef(function Transition(props, ref) {
  return <Slide direction="up" ref={ref} {...props} />;
});

const ConfirmationDialog = (props) => {
  const {
    dialogTitle,
    dialogOpen,
    onClose,
    action,
    buttonLabel,
    confirmationText,
    btnColor,
  } = props;
  return (
    <>
      <MDDialog
        dialogTitle={dialogTitle}
        dialogOpen={dialogOpen}
        dialogClose={onClose}
        TransitionComponent={Transition}
        maxWidth="sm"
      >
        <DialogContent dividers>
          <Typography variant="subtitle1" fontSize={16} fontWeight="regular">
            {confirmationText
              ? confirmationText
              : "Are you sure you want to Delete ?"}
          </Typography>
        </DialogContent>

        <DialogActions>
          <Stack
            direction="row"
            spacing={2}
            alignItems="center"
            justifyContent="end"
          >
            <MDTextButton onClick={() => onClose()}>Cancel</MDTextButton>
            <MDButton
              size="small"
              variant="contained"
              color={btnColor ? btnColor : "primary"}
              onClick={action}
            >
              {buttonLabel ? buttonLabel : "Delete"}
            </MDButton>
          </Stack>
        </DialogActions>
      </MDDialog>
    </>
  );
};

export default ConfirmationDialog;
