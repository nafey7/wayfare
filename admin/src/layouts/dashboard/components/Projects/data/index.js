// @mui material components
import Tooltip from "@mui/material/Tooltip";
import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MDAvatar from "components/MDAvatar";
import MDProgress from "components/MDProgress";

// Images
import logoXD from "assets/images/small-logos/logo-xd.svg";
import logoAtlassian from "assets/images/small-logos/logo-atlassian.svg";
import logoSlack from "assets/images/small-logos/logo-slack.svg";
import logoSpotify from "assets/images/small-logos/logo-spotify.svg";
import logoJira from "assets/images/small-logos/logo-jira.svg";
import logoInvesion from "assets/images/small-logos/logo-invision.svg";
import team1 from "assets/images/team-1.jpg";
import team2 from "assets/images/team-2.jpg";
import team3 from "assets/images/team-3.jpg";
import team4 from "assets/images/team-4.jpg";

export default function data() {
  const avatars = (members) =>
    members.map(([image, name]) => (
      <Tooltip key={name} title={name} placeholder="bottom">
        <MDAvatar
          src={image}
          alt="name"
          size="xs"
          sx={{
            border: ({ borders: { borderWidth }, palette: { white } }) =>
              `${borderWidth[2]} solid ${white.main}`,
            cursor: "pointer",
            position: "relative",

            "&:not(:first-of-type)": {
              ml: -1.25,
            },

            "&:hover, &:focus": {
              zIndex: "10",
            },
          }}
        />
      </Tooltip>
    ));

  const Company = ({ image, name }) => (
    <MDBox display="flex" alignItems="center" lineHeight={1}>
      <MDAvatar src={image} name={name} size="sm" />
      <MDTypography variant="button" fontWeight="medium" ml={1} lineHeight={1}>
        {name}
      </MDTypography>
    </MDBox>
  );

const users = [
  {
  "name":"Loren Dev",
  "amount":"$75",
  "bookings":"5",

},
{
  "name":"John Wich",
  "amount":"$65",
  "bookings":"7",

},
{
  "name":"Snow White",
  "amount":"$25",
  "bookings":"3",

},
{
  "name":"Branden Strom",
  "amount":"$19",
  "bookings":"10",

},
]

  return {
    columns: [
      {
        Header: "Name",
        accessor: "name",
        width: "30%",
        align: "left",
      },
      {
        Header: "No OF Bookings",
        accessor: "bookings",
        width: "40%",
        align: "left",
      },
      { Header: "Amount", accessor: "amount", width: "30%", align: "center" },
    ],

    rows: users.map((user, index) => ({
      name: (
        <MDBox display="flex" color="text" py={1}>
          {user.name}
        </MDBox>
      ),
      bookings: (
        <MDTypography variant="caption" color="text" fontWeight="medium">
          {user.bookings}
        </MDTypography>
      ),
      amount: (
        <MDBox width="8rem" textAlign="center">
           <MDTypography variant="caption" color="text" fontWeight="medium">
          {user.amount}
        </MDTypography>
        </MDBox>
      ),
      key: index, // Add a unique key for each row
    })),
  };
}
