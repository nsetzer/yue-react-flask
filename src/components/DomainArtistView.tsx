
import * as React from 'react';
import PropTypes from 'prop-types';
import { Link } from 'react-router-dom'
import { bindActionCreators } from 'redux';
import { connect } from 'react-redux';
import Button from 'material-ui/Button';

import Grid from 'material-ui/Grid';

import * as UiCard from 'material-ui/Card';
const Card = UiCard.default

import * as UiList  from 'material-ui/List';
const List = UiList.default
const ListItem = UiList.ListItem
const ListItemIcon = UiList.ListItemIcon
const ListItemText = UiList.ListItemText
const ListItemSecondaryAction = UiList.ListItemSecondaryAction
import IconButton from 'material-ui/IconButton';
import Send from 'material-ui-icons/Send';
import Delete from 'material-ui-icons/Delete';
import NavigateBefore from 'material-ui-icons/NavigateBefore';

import * as libraryActionCreators from '../actions/library';
import * as queueActionCreators from '../actions/queue';
const actionCreators = Object.assign({},
                                     libraryActionCreators,
                                     queueActionCreators);

import History from '../history'
import MoreVert from 'material-ui-icons/MoreVert';

import Typography from 'material-ui/Typography';

export interface DomainArtistViewProps {
  match: any
  libraryStatus: string,
  libraryGetDomainInfo: () => any,
  createQueue: (q,m) => any,
  domain_artists: Array<any>,
  domain_genres: Array<any>,
  domain_song_count: number
};

export interface DomainArtistViewState {
}

const MediumIconStyle = {
    width: "32px",
    height: "32px",
}

function navigateTo(url) {
  History.push(url)
  window.scrollTo(0,0)
}

function navigateBack() {
  History.goBack()
  window.scrollTo(0,0)
}

class DomainArtistView extends React.Component<DomainArtistViewProps,DomainArtistViewState> {

  constructor(props) {
    super(props);
    this.componentDidMount = this.componentDidMount.bind(this)
  }

  componentDidMount() {

    // TODO: this query only needs to run once, find a better
    // way to gate that behavior
    if(this.props.domain_song_count == 0) {
      this.props.libraryGetDomainInfo();
    }
  }

  render() {

    let artist_name = this.props.match.params.artist
    let albums = {}
    for (let i=0; i < this.props.domain_artists.length; i++) {
      let artist = this.props.domain_artists[i]
      if (artist.name == artist_name) {
        albums = artist.albums;
        break;
      }
    }

    let names = Object.keys(albums)
    names.sort()

    return (
        <div>

        <Grid container spacing={24} justify="center">
            <Grid item  xs={2}>
              <IconButton onClick={(e) => navigateBack()}>
                <NavigateBefore style={MediumIconStyle} />
              </IconButton>
            </Grid>
            <Grid item  xs={8}>
            <Typography type="title" align="center" gutterBottom noWrap>
              {this.props.match.params.artist}
            </Typography>
            </Grid>
            <Grid item  xs={2}>
            <IconButton onClick={(e) => navigateBack()}>
                <MoreVert style={MediumIconStyle} />
              </IconButton>
            </Grid>
        </Grid>

        <Button
          raised
          color="accent"
          onClick={(e) => {
            this.props.createQueue(`artist="${artist_name}"`, 'random')}
        }>
          Random Play All
        </Button>

        <List>

            <Card style={{marginLeft:"8px",
                                       marginRight:"8px",
                                       marginTop:"5px",
                                       marginBottom:"5px"}}>
            <ListItem
                      button
                      onClick={()=>{navigateTo("/main/library/"+artist_name +"/$all")}}>
               <ListItemText primary={"All Songs"} />
               <ListItemSecondaryAction>
                 <IconButton onClick={() => {}}>
                   <MoreVert />
                 </IconButton>
               </ListItemSecondaryAction>
            </ListItem>
            </Card>

            {

              (names.length>0) ?
                names.map( (album) => {
                  return <Card style={{marginLeft:"8px",
                                       marginRight:"8px",
                                       marginTop:"5px",
                                       marginBottom:"5px"}}
                                key={album}>
                            <ListItem button
                                     onClick={()=>{navigateTo("/main/library/"+artist_name +"/" + album)}}>
                              <ListItemText primary={album}
                                            secondary={albums[album] + " Songs"} />
                              <ListItemSecondaryAction>
                                <IconButton onClick={() => {}}>
                                  <MoreVert />
                                </IconButton>
                              </ListItemSecondaryAction>
                           </ListItem>
                          </Card>
                }) : <div>No Artists To Display</div>
            }
         </List>

        </div>
    )
  }
}
function mapStateToProps(state) {
  return {
      libraryStatus: state.library.statusText,
      domain_artists: state.library.domain_artists,
      domain_genres: state.library.domain_genres,
      domain_song_count: state.library.domain_song_count,
    };
}

function mapDispatchToProps(dispatch) {
  return bindActionCreators(actionCreators, dispatch);
}

export default connect(
  mapStateToProps,
  mapDispatchToProps
)(DomainArtistView);