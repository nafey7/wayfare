import React from "react";
import { styled } from "@mui/material/styles";
import CardHeader from "@mui/material/CardHeader";

const CustomCardHeader = styled(CardHeader)(({ theme, other }) => ({
  borderBottomWidth: other?.border ? other?.border : 0,
  borderBottomStyle: "solid",
  borderBottomColor: "#e9ebec",
  padding: "12px 24px",
  backgroundColor:
    other?.bgcolor || other?.bgcolorvariant
      ? theme.palette[other?.bgcolor][other?.bgcolorvariant]
      : theme.palette.background.paper,
  ".MuiCardHeader-title": {
    fontSize: other.titlesize ?? "1rem",
    fontWeight: other.titleweight ?? 700,
    color:
      other?.titlecolor && other?.titlecolorvariant
        ? theme.palette[other?.titlecolor][other?.titlecolorvariant]
        : theme.palette.text.primary,
    [theme.breakpoints.down("sm")]: {
      fontSize: other.titlesize ?? "0.875rem",
    },
  },
}));

const CMCardHeader = (props) => {
  const { children, ...rest } = props;
  return (
    <>
      <CustomCardHeader other={props} {...rest}>
        {children}
      </CustomCardHeader>
    </>
  );
};

export default CMCardHeader;
