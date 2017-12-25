
import * as React from 'react';
import PropTypes from 'prop-types';
import { Link } from 'react-router-dom'
import { bindActionCreators } from 'redux';
import { connect } from 'react-redux';
import Button from 'material-ui/Button';

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

import * as actionCreators from '../actions/library';

import History from '../history'
import MoreVert from 'material-ui-icons/MoreVert';

import Typography from 'material-ui/Typography';

export interface IDomainArtistViewProps {
  match: any
  libraryStatus: string,
  libraryGetDomainInfo: () => any,
  domain_artists: Array<any>,
  domain_genres: Array<any>,
  domain_song_count: number
};

export interface IDomainArtistViewState {
}

function navigateTo(url) {
  History.push(url)
  window.scrollTo(0,0)
}

function navigateBack() {
  History.goBack()
  window.scrollTo(0,0)
}

class DomainGenreView extends React.Component<IDomainArtistViewProps,IDomainArtistViewState> {

  constructor(props) {
    super(props);
    this.componentDidMount = this.componentDidMount.bind(this)
  }

  public componentDidMount() {

    // TODO: this query only needs to run once, find a better
    // way to gate that behavior
    if(this.props.domain_song_count == 0) {
      this.props.libraryGetDomainInfo();
    }
  }

  public render() {

    let genres = this.props.domain_genres

    return (
        <div>
        <IconButton onClick={(e) => navigateBack()}>
          <NavigateBefore />
        </IconButton>
        <Typography type="title" align="center" gutterBottom>
          Genres
        </Typography>

        <List>

            {

              (genres.length>0) ?
                genres.map( (genre) => {
                  return <Card style={{marginLeft:"8px",
                                       marginRight:"8px",
                                       marginTop:"5px",
                                       marginBottom:"5px"}}
                               key={genre.name}>
                            <ListItem button
                                     onClick={()=>{navigateTo("/main/genres/view?genre="+genre.name)}}>
                              <ListItemText primary={genre.name}
                                            secondary={genre.artist_count + " Artists. " +genre.count + " Songs"} />
                              <ListItemSecondaryAction>
                                <IconButton onClick={() => {}}>
                                  <MoreVert />
                                </IconButton>
                              </ListItemSecondaryAction>
                           </ListItem>
                          </Card>
                }) : <div>No Genres To Display</div>
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
)(DomainGenreView);
