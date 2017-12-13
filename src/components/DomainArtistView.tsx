
import * as React from 'react';
import PropTypes from 'prop-types';
import { Link } from 'react-router-dom'
import { bindActionCreators } from 'redux';
import { connect } from 'react-redux';
import Button from 'material-ui/Button';

import * as UiList  from 'material-ui/List';
const List = UiList.default
const ListItem = UiList.ListItem
const ListItemIcon = UiList.ListItemIcon
const ListItemText = UiList.ListItemText
const ListItemSecondaryAction = UiList.ListItemSecondaryAction
import IconButton from 'material-ui/IconButton';
import Send from 'material-ui-icons/Send';
import Delete from 'material-ui-icons/Delete';

import * as actionCreators from '../actions/library';

import History from '../history'

export interface DomainArtistViewProps {
  match: any
  libraryStatus: string,
  libraryGetDomainInfo: () => any,
  domain_artists: Array<any>,
  domain_genres: Array<any>,
  domain_song_count: number
};

export interface DomainArtistViewState {
}

class DomainArtistView extends React.Component<DomainArtistViewProps,DomainArtistViewState> {

  constructor(props) {
    super(props);
    this.componentDidMount = this.componentDidMount.bind(this)
  }

  componentDidMount() {

    // TODO: this query only needs to run once, find a better
    // way to gate that behavior
    if(this.props.domain_song_count==0) {
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
        console.log(artist)
        break;
      }
    }

    let names = Object.keys(albums)
    names.sort()

    console.log(window.location)

    return (
        <div>
        <h1>{this.props.match.params.artist}</h1>
        <Button
            onClick={(e) => History.goBack()}
          >Go Back</Button>

        <List>
            <ListItem>
                <Link to={"/main/library/"+artist_name +"/$all"}>All Songs</Link>
            </ListItem>

            {

              (names.length>0) ?
                names.map( (album) => {
                  return <ListItem key={album}>
                           <Link to={"/main/library/"+artist_name +"/" + album}>{album}</Link>
                         </ListItem>
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