
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
import MoreVert from 'material-ui-icons/MoreVert';

import * as libraryActionCreators from '../actions/library';
import * as queueActionCreators from '../actions/queue';
const actionCreators = Object.assign({},
                                     libraryActionCreators,
                                     queueActionCreators);

import Typography from 'material-ui/Typography';

import History from '../history';

import * as UiCard from 'material-ui/Card';
const Card = UiCard.default

export interface IDomainViewProps {
  match: any
  location: any
  libraryStatus: string,
  libraryGetDomainInfo: () => any,
  createQueue: (q,m) => any,
  domain_artists: Array<any>,
  domain_genres: Array<any>,
  domain_song_count: number
};

export interface IDomainViewState {
  filter_genres: Array<any>;
}

function parseQuery(queryString) {
    let query = {genre: null};
    let pairs = (queryString[0] === '?' ? queryString.substr(1) : queryString).split('&');
    for (let i = 0; i < pairs.length; i++) {
        let pair = pairs[i].split('=');
        query[decodeURIComponent(pair[0])] = decodeURIComponent(pair[1] || '');
    }
    return query;
}

function navigateTo(url) {
  History.push(url)
  window.scrollTo(0,0)
}

function navigateBack() {
  History.goBack()
  window.scrollTo(0,0)
}

function str_array_eq(ar1, ar2) {
  // first check that the arrays are of equal length
  if (ar1.length != ar2.length) {
    return false;
  }
  // check that the contents are the same
  for (let i=0; i < ar1.length; i++) {
    if (ar1[i] != ar2[i]) {
      return false
    }
  }

  return true;
}

class DomainView extends React.Component<IDomainViewProps,IDomainViewState> {

  constructor(props) {
    super(props);
    this.state = {filter_genres: []}
    this.componentDidMount = this.componentDidMount.bind(this)
  }

  public componentWillMount() {
    let query_params: {genre:string} = parseQuery(this.props.location.search);

    let genres = []
    if (query_params.genre !== null) {
      genres = [query_params.genre, ]
    }

    if (!str_array_eq(genres, this.state.filter_genres)) {
      this.setState({filter_genres: genres})
    }

  }

  public componentWillReceiveProps(newProps) {
    let query_params: {genre:string} = parseQuery(newProps.location.search);

    let genres = []
    if (query_params.genre !== null) {
      genres = [query_params.genre, ]
    }

    if (!str_array_eq(genres, this.state.filter_genres)) {
      this.setState({filter_genres: genres})
    }

  }

  public componentDidMount() {

    // TODO: this query only needs to run once, find a better
    // way to gate that behavior
    // console.log(this.props.match.params)

    // let genre = this.props.match.params.genre

    if(this.props.domain_song_count==0) {
      this.props.libraryGetDomainInfo();
    }
  }

  public render() {

    let artists = (this.props.domain_artists.length>0)?
                  this.props.domain_artists:[]

    let genres = this.state.filter_genres;
    if (genres && genres.length > 0) {
      artists = artists.filter( (art) => {
        return art.genres.includes(genres[0])
      });
    }

    // note: this is a hack to enable search by genre
    // assumption is that genre is unstructured data
    // however, we are now forcing it to be a semicolon separated list
    // that is terminated by a semicolon. therefore if i do a wild card
    // search in the database (e.g. "*;foo;*" ) I should find exactly
    // that genre
    const queryString = genres.map( x => `genre=\";${x};\"`).join(" ");


    return (
        <div>
        <Typography type="title" align="center" gutterBottom>
          Artists
        </Typography>

        <Button
          raised
          color="accent"
          onClick={(e) => {
            this.props.createQueue(queryString, 'random')}
        }>
          Random Play All
        </Button>

        <List>
            {
              (artists.length>0)?
                artists.map( (artist) => {
                  return <Card style={{marginLeft:"8px",
                                       marginRight:"8px",
                                       marginTop:"5px",
                                       marginBottom:"5px"}}
                                key={artist.name}>
                            <ListItem button
                                     onClick={()=>{navigateTo("/main/library/"+artist.name)}}>
                              <ListItemText primary={artist.name}
                                            secondary={Object.keys(artist.albums).length + " Albums. " + artist.count + " Songs"} />
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
)(DomainView);