import React from "react";

import Button from "@mui/material/Button";
import { styled } from "@mui/material/styles";
import PropTypes from "prop-types";

const RootStyle = styled(Button)(({ theme, ownerState }) => {
  const { color } = ownerState;
  return {
    boxShadow: "none",
    backgroundColor: "transparent",
    padding: "0",
    color: theme.palette.grey[600],
    minHeight: 0,
    height: "fit-content",
    transition: (theme) =>
      theme.transitions.create("all", {
        easing: theme.transitions.easing.easeOut,
        duration: theme.transitions.duration.shortest,
      }),
    "&:hover,&:active,&:focus": {
      color: theme.palette.grey[700],
      backgroundColor: "transparent",
      boxShadow: "none",
      transition: (theme) =>
        theme.transitions.create("all", {
          easing: theme.transitions.easing.easeOut,
          duration: theme.transitions.duration.shortest,
        }),
    },
    ...(color !== "default"
      ? {
          color: theme.palette[color].main,
          ":hover,:active,:focus": {
            color: theme.palette[color].dark,
          },
        }
      : null),
  };
});

const MDTextButton = (props) => {
  const { color = "default", label, children, sx, ...rest } = props;

  return (
    <>
      <RootStyle disableRipple ownerState={{ color }} sx={{ ...sx }} {...rest}>
        {label}
        {children}
      </RootStyle>
    </>
  );
};

MDTextButton.propTypes = {
  color: PropTypes.string,
  label: PropTypes.string,
  sx: PropTypes.any,
  children: PropTypes.any,
};
export default MDTextButton;
