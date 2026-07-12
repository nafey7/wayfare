import React, { memo } from "react";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Icon from "@mui/material/Icon";
import IconButton from "@mui/material/IconButton";
import Slide from "@mui/material/Slide";
import { styled, useTheme } from "@mui/material/styles";
import MDTypography from "components/MDTypography";
import PropTypes from "prop-types";
import { useMaterialUIController } from "context";

const Transition = React.forwardRef(function Transition(props, ref) {
  return <Slide direction="up" ref={ref} {...props} />;
});

const BootstrapDialog = styled(Dialog)(({ theme }) => ({
  "& .MuiDialogContent-root": {
    padding: theme.spacing(2),
    borderColor: theme.palette.grey[200],
  },
  "& .MuiDialogActions-root": {
    padding: theme.spacing(1),
  },
}));

export const BootstrapDialogTitle = (props) => {
  const { children, onClose, closeIcon, ...other } = props;
  return (
    <DialogTitle
      component="div"
      sx={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        m: 0,
        py: 1,
        px: 2,
      }}
      {...other}
    >
      <MDTypography variant="h6" fontWeight="medium">
        {children}
      </MDTypography>
      {closeIcon ? (
        <IconButton
          aria-label="close"
          onClick={onClose}
          sx={{
            backgroundColor: (theme) => theme.palette.grey[500],
            color: "primary.contrastText",
            "&:hover,&:focus": {
              backgroundColor: (theme) => theme.palette.grey[600],
              color: "primary.contrastText",
            },
          }}
          size="small"
        >
          <Icon>close</Icon>
        </IconButton>
      ) : null}
    </DialogTitle>
  );
};

BootstrapDialogTitle.propTypes = {
  children: PropTypes.node,
  onClose: PropTypes.func.isRequired,
};

const MDDialogRoot = (props) => {
  const [controller] = useMaterialUIController();
  const { darkMode } = controller;
  const {
    dialogOpen,
    dialogClose,
    closeIcon,
    dialogTitle,
    dialogContent,
    dialogAction,
    children,
    maxWidth,
    minWidth,
    dividers,
    rounded,
    sx,
    ...rest
  } = props;
  const theme = useTheme();

  return (
    <>
      <BootstrapDialog
        TransitionComponent={Transition}
        open={dialogOpen}
        onClose={(event, reason) => {
          if (reason !== "backdropClick") {
            dialogClose(event, reason);
          }
        }}
        aria-labelledby="customized-dialog-title"

        sx={{
          "& .MuiDialog-paper": {
            [theme.breakpoints.down("sm")]: {
              margin: { xs: 2 },
            },
            borderRadius:
              props.borderRadius === false
                ? "0px"
                : rounded && props.fullWidth
                  ? "20px 20px 0 0"
                  : "20px",
            backgroundColor: darkMode ? "#1a2035" : "#ffffff",
            minWidth: minWidth && minWidth,
            maxWidth: maxWidth ? maxWidth : "lg",

          },
          ...sx,
        }}
        {...rest}
      >
        {dialogTitle && (
          <BootstrapDialogTitle
            id="customized-dialog-title"
            onClose={dialogClose}
            closeIcon={closeIcon}
            other={props}
          >
            {dialogTitle}
          </BootstrapDialogTitle>
        )}
        {dialogContent && (
          <DialogContent dividers={dividers ? dividers : true}>
            {dialogContent}
          </DialogContent>
        )}
        {dialogAction && <DialogActions>{dialogAction}</DialogActions>}
        {children}
      </BootstrapDialog>
    </>
  );
};

export default memo(MDDialogRoot);
