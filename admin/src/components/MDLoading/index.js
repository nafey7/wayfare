import { forwardRef } from "react";
import CircularProgress from '@mui/material/CircularProgress';
import Box from '@mui/material/Box';
import Backdrop from '@mui/material/Backdrop';
import { getRandomEmoji } from "global/functions";

const CircularIndeterminate = forwardRef(({ type, ...rest }, ref) => (
    type === "full" ?
        <Backdrop
            sx={{ color: '#fff', zIndex: 999999 }}
            open={rest?.open}
        >
            {rest?.text ?
                <>
                   {getRandomEmoji()} {rest?.text} <CircularProgress
                        ref={ref}
                        {...rest}
                    />
                </>
                : <CircularProgress ref={ref} {...rest}/>
            }
        </Backdrop>
        :
        <Box sx={{ display: 'flex' }}>
            <CircularProgress ref={ref} {...rest} />
        </Box>
));

CircularIndeterminate.defaultProps = {
    color: "white"
};

export default CircularIndeterminate;
