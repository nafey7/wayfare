import { styled } from "@mui/material/styles";
import Switch from "@mui/material/Switch";

const CustomizedSwitch = styled(Switch)(({ theme, checked }) => ({
  // padding: 8,
  "& .MuiSwitch-track": {
    // borderRadius: 22 / 2,
    background: checked ? "green" : "red",
    "&:before, &:after": {
      content: '""',
      position: "absolute",
      top: "50%",
      transform: "translateY(-50%)",
      width: 16,
      height: 16,
    },
    "&:before": {
      // backgroundImage: `url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" height="16" width="16" viewBox="0 0 24 24"><path fill="${encodeURIComponent(
      //   "green"
      // )}" d="M21,7L9,19L3.5,13.5L4.91,12.09L9,16.17L19.59,5.59L21,7Z"/></svg>')`,
      left: 12,
    },
    "&:after": {
      // backgroundImage: `url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" height="16" width="16" viewBox="0 0 24 24"><path fill="red" d="M18.38 5.62 17.62 5 12 10.62 6.38 5 5.62 5.62 11.24 11.24 5.62 16.86 6.38 17.48 12 12.86 17.62 18.48 18.38 17.86 12.76 12.24 18.38 6.62 17.62 5.38z"/></svg>')`,
      // backgroundImage: `url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" height="16" width="16" viewBox="0 0 24 24"><path fill="${encodeURIComponent(
      //  "red"
      // )}" d="M19,13H5V11H19V13Z" /></svg>')`,
      right: 12,
    },
  },
  "& .MuiSwitch-thumb": {
  //   boxShadow: "none",
  //   width: 16,
  //   height: 16,
  //   margin: 2,
  },
}));

const MDSwitch = (props) => {
  const { checked, ...rest } = props;
  return <CustomizedSwitch checked={checked} {...rest} />;
};
export default MDSwitch;
