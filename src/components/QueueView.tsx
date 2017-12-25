
import * as React from 'react';
import PropTypes from 'prop-types';
import { bindActionCreators } from 'redux';
import { connect } from 'react-redux';

import * as UiCard from 'material-ui/Card';
const Card = UiCard.default

import Typography from 'material-ui/Typography';

import Button from 'material-ui/Button';

import * as actionCreators from '../actions/queue';

import * as UiList  from 'material-ui/List';
const List = UiList.default
const ListItem = UiList.ListItem
const ListItemIcon = UiList.ListItemIcon
const ListItemText = UiList.ListItemText
const ListItemSecondaryAction = UiList.ListItemSecondaryAction
import IconButton from 'material-ui/IconButton';
import Send from 'material-ui-icons/Send';
import Delete from 'material-ui-icons/Delete';
import MoreVert from 'material-ui-icons/MoreVert';
import Menu, { MenuItem } from 'material-ui/Menu';

import {
  fmtDuration,
  getSongAudioUrl,
  getSongArtUrl,
  getSongDisplayTitle,
} from '../utils/misc'

export interface IMenuOpts {
  open: boolean,
  anchorEl: any,
  index: number,
  song: any
}

export interface IQueueViewProps {
  queueStatus: string,
  songs: Array<any>,
  history: Array<any>,
  getQueue: () => any,
  setQueue: () => any,
  populateQueue: () => any,
  playIndexInQueue: (index: number) => any,
  playNextInQueue: (index: number) => any,
  deleteIndexInQueue: (index: number) => any,
};

export interface IQueueViewState {
  menuOpts: IMenuOpts
}

const listRightStyle: React.CSSProperties = {
  position: "absolute",
  right: "32px",
};

class QueueView extends React.Component<IQueueViewProps,IQueueViewState> {

  constructor(props) {
    super(props);
    this.state = {menuOpts:{open:false, anchorEl:null, song: null, index: -1}}

    this.onOpenMenu = this.onOpenMenu.bind(this)
    this.onMenuClose = this.onMenuClose.bind(this)
    this.onMenuPlay = this.onMenuPlay.bind(this)
    this.onMenuPlayNext = this.onMenuPlayNext.bind(this)
    this.onMenuRemove = this.onMenuRemove.bind(this)
  }

  public onOpenMenu(event, index, song) {
    let menuOpts = this.state.menuOpts;
    menuOpts.open = true;
    menuOpts.anchorEl = event.currentTarget
    menuOpts.index = index
    menuOpts.song = song
    this.setState({menuOpts: menuOpts});
  }

  public onMenuClose() {
    let menuOpts = this.state.menuOpts;
    menuOpts.open = false;
    this.setState({menuOpts: menuOpts});
  }

  public onMenuPlay() {
    let menuOpts = this.state.menuOpts;
    let index = menuOpts.index;
    menuOpts.open = false;
    this.setState({menuOpts: menuOpts});
    this.props.playIndexInQueue(index)
  }

  public onMenuPlayNext() {

    let menuOpts = this.state.menuOpts;
    let index = menuOpts.index;
    menuOpts.open = false;
    this.setState({menuOpts: menuOpts});
    this.props.playNextInQueue(index)
  }

  public onMenuRemove() {
    let menuOpts = this.state.menuOpts;
    let index = menuOpts.index;
    menuOpts.open = false;
    this.setState({menuOpts: menuOpts});
    this.props.deleteIndexInQueue(index)
  }

  public render() {
    return (
        <div>
        <IconButton aria-label="Populate"
             onClick={() => {this.props.populateQueue()}}>
              <Send />
        </IconButton>
        <Typography noWrap>
        <List>
            {
              (this.props.songs && this.props.songs.length>0) ?
                this.props.songs.map( (song, index) => {
                  return <Card style={{marginLeft:"8px",
                                       marginRight:"8px",
                                       marginTop:"5px",
                                       marginBottom:"5px"}}
                                key={song.id}>
                          <ListItem>
                             <ListItemText primary={song.title}
                                           secondary={song.artist}/>
                             <ListItemText style={listRightStyle}
                                           primary={fmtDuration(song.length)}/>
                             <ListItemSecondaryAction>
                               <IconButton aria-label="Delete"
                                           onClick={(e) => {this.onOpenMenu(e,index,song)}}>
                                <MoreVert />
                               </IconButton>
                             </ListItemSecondaryAction>
                          </ListItem>
                         </Card>
                }) : <div>No Songs To Display</div>
            }
        </List>
        </Typography>

        <Menu
          id="simple-menu"
          anchorEl={this.state.menuOpts.anchorEl}
          open={this.state.menuOpts.open}
          onRequestClose={this.onMenuClose}>
          {(this.state.menuOpts.index>0)?
            <MenuItem onClick={this.onMenuPlay}>Play</MenuItem>
            :null}
          {(this.state.menuOpts.index>1)?
            <MenuItem onClick={this.onMenuPlayNext}>Play Next</MenuItem>
            :null}
          {(this.state.menuOpts.index>0)?
            <MenuItem onClick={this.onMenuRemove}>Remove</MenuItem>
            :null}
        </Menu>

        </div>
    );
  }
}

function mapStateToProps(state) {
  return {
      queueStatus: state.queue.statusText,
      songs: state.queue.songs,
      history: state.queue.history,
    };
}

function mapDispatchToProps(dispatch) {
  return bindActionCreators(actionCreators, dispatch);
}

export default connect(
  mapStateToProps,
  mapDispatchToProps
)(QueueView);
